import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.graph import run_query

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

    return QueryResponse(
        question=result["question"],
        sql=result["sql"],
        rows=result["rows"],
        chart=result["chart"],
        insight=result["insight"],
        retries=result["retry_count"],
        error=result["error"],
    )
