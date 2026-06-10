import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.graph import run_query
from agent.tools import log_query, get_history

app = FastAPI(
    title="SQL Business Intelligence Agent",
    description="Natural language → SQL → chart + insight",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str
    provider: str | None = None  # "openai" or "groq" — overrides .env


class QueryResponse(BaseModel):
    question: str
    sql: str
    rows: list[dict]
    chart: dict | None
    insight: str
    retries: int
    error: str | None


class HistoryItem(BaseModel):
    id: int
    question: str
    sql: str | None
    row_count: int | None
    insight: str | None
    error: str | None
    retry_count: int
    created_at: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    if request.provider:
        os.environ["LLM_PROVIDER"] = request.provider

    try:
        result = run_query(request.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        log_query(
            question=result["question"],
            sql=result["sql"],
            row_count=len(result["rows"]),
            insight=result["insight"],
            error=result["error"],
            retry_count=result["retry_count"],
        )
    except Exception:
        pass  # never let history logging break the main response

    return QueryResponse(
        question=result["question"],
        sql=result["sql"],
        rows=result["rows"],
        chart=result["chart"],
        insight=result["insight"],
        retries=result["retry_count"],
        error=result["error"],
    )


@app.get("/history", response_model=list[HistoryItem])
def history(limit: int = 20):
    try:
        return [
            {**item, "created_at": str(item["created_at"])}
            for item in get_history(limit)
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
