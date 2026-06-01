# SQL Business Intelligence Agent

A natural language BI agent that lets business users query a database in plain English and get back SQL results, visualizations, and AI-generated insights — no SQL knowledge required.

> Ask: *"Show me MRR trend for the last 12 months"*
> Get back: the SQL, a line chart, and a plain-English explanation.

---

## Features

- **Natural Language → SQL** — LLM translates plain English questions into accurate SQL queries
- **Self-Correcting Agent** — if the generated SQL fails, the agent automatically diagnoses the error and rewrites the query (LangGraph retry loop)
- **Auto Visualization** — agent decides the best chart type (line, bar, pie) and renders it with Plotly
- **Plain-English Insights** — LLM explains the result in business terms, not database terms
- **Schema-Aware** — agent introspects the live database schema before generating SQL, so it always knows what tables and columns exist
- **Multi-LLM Support** — switch between OpenAI (GPT-4o) and Groq (Llama 3.3) via a single environment variable

---

## Architecture

```
User Question (Streamlit UI)
         │
         ▼
   ┌─────────────┐
   │ FastAPI API │
   └──────┬──────┘
          │
          ▼
   ┌──────────────────────────────────────┐
   │           LangGraph Agent           │
   │                                     │
   │  1. get_schema   ──► DB introspect  │
   │  2. generate_sql ──► LLM           │
   │  3. execute_sql  ──► PostgreSQL    │
   │       │ error?                      │
   │  4. self_correct ──► LLM rewrite   │  (retry up to 3x)
   │  5. build_chart  ──► Plotly JSON   │
   │  6. generate_insight ──► LLM      │
   └──────────────────────────────────────┘
          │
          ▼
   SQL + Chart + Insight (rendered in Streamlit)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Orchestration | LangGraph |
| LLM | OpenAI GPT-4o / Groq Llama 3.3-70b |
| Database | PostgreSQL 16 |
| ORM / DB Client | SQLAlchemy |
| Backend API | FastAPI |
| Frontend | Streamlit |
| Visualization | Plotly |
| Containerization | Docker + Docker Compose |

---

## Sample Dataset

The project ships with a realistic SaaS metrics dataset:

| Table | Description |
|---|---|
| `companies` | Customer accounts — plan, industry, signup date |
| `subscriptions` | Subscription history — MRR, start/end dates, status |
| `events` | Lifecycle events — signups, upgrades, downgrades, churns |
| `invoices` | Billing records — amount, date, payment status |

**Example questions you can ask:**
- "What is our MRR trend over the last 12 months?"
- "Which plan has the highest churn rate?"
- "Show me the top 10 companies by MRR"
- "How many new customers signed up each month this year?"
- "What percentage of revenue comes from enterprise vs starter plans?"
- "Which industry has the lowest average MRR?"

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- An API key from [OpenAI](https://platform.openai.com) or [Groq](https://console.groq.com) (Groq has a free tier)

### 1. Clone and configure

```bash
git clone <repo-url>
cd sql-bi-agent

cp .env.example .env
# Edit .env and add your API key
```

### 2. Choose your LLM provider

In `.env`:

```bash
# Use Groq (free, fast)
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...

# OR use OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### 3. Start everything

```bash
docker compose up --build
```

This starts PostgreSQL (with sample data auto-loaded), the FastAPI backend, and the Streamlit UI.

### 4. Open the UI

Go to [http://localhost:8501](http://localhost:8501) and start asking questions.

---

## Running Locally (without Docker)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start PostgreSQL separately, then:
cp .env.example .env  # fill in DATABASE_URL

uvicorn api.main:app --reload &
streamlit run ui/app.py
```

---

## Project Structure

```
sql-bi-agent/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── data/
│   └── seed.sql              # SaaS sample data
├── agent/
│   ├── graph.py              # LangGraph workflow definition
│   ├── tools.py              # SQL executor + chart builder tools
│   ├── prompts.py            # LLM system prompts
│   └── llm.py                # OpenAI / Groq client factory
├── api/
│   └── main.py               # FastAPI — POST /query endpoint
└── ui/
    └── app.py                # Streamlit chat interface
```

---

## API Reference

### `POST /query`

Run a natural language query against the database.

**Request:**
```json
{
  "question": "Show me MRR trend for the last 6 months",
  "provider": "groq"
}
```

**Response:**
```json
{
  "question": "Show me MRR trend for the last 6 months",
  "sql": "SELECT DATE_TRUNC('month', ...) ...",
  "rows": [...],
  "chart": { "data": [...], "layout": {...} },
  "insight": "MRR has grown 23% over the past 6 months, with the strongest growth in March...",
  "retries": 0
}
```

---

## How the Self-Correction Works

When the SQL executor encounters a database error, the agent doesn't give up. Instead, it passes the original question, the failed SQL, and the error message back to the LLM with a correction prompt. The LLM rewrites the SQL avoiding the same mistake. This loop runs up to 3 times before returning a graceful failure message — mimicking how a human analyst would debug a query.

---

## License

MIT
