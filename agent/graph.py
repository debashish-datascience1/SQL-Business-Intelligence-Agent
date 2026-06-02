import json
from typing import TypedDict
from langgraph.graph import StateGraph, END

from agent.llm import chat
from agent.tools import fetch_schema, execute_sql, build_chart
from agent.prompts import (
    SQL_SYSTEM, SQL_CORRECTION_SYSTEM, CHART_SYSTEM, INSIGHT_SYSTEM,
    sql_user_prompt, sql_correction_user_prompt,
    chart_user_prompt, insight_user_prompt,
)


class AgentState(TypedDict):
    question: str
    schema: str
    sql: str
    rows: list[dict]
    error: str | None
    retry_count: int
    chart_config: dict | None
    chart: dict | None
    insight: str


# ── Nodes ─────────────────────────────────────────────────────────────────────

def node_get_schema(state: AgentState) -> dict:
    return {"schema": fetch_schema()}


def node_generate_sql(state: AgentState) -> dict:
    messages = [
        {"role": "system", "content": SQL_SYSTEM},
        {"role": "user",   "content": sql_user_prompt(state["schema"], state["question"])},
    ]
    sql = chat(messages).strip()
    # Strip markdown fences if the LLM ignores instructions
    if sql.startswith("```"):
        sql = "\n".join(
            line for line in sql.splitlines()
            if not line.startswith("```")
        ).strip()
    return {"sql": sql}


def node_execute_sql(state: AgentState) -> dict:
    rows, error = execute_sql(state["sql"])
    return {"rows": rows, "error": error}


def node_self_correct(state: AgentState) -> dict:
    messages = [
        {"role": "system", "content": SQL_CORRECTION_SYSTEM},
        {"role": "user",   "content": sql_correction_user_prompt(
            state["schema"], state["question"], state["sql"], state["error"]
        )},
    ]
    sql = chat(messages).strip()
    if sql.startswith("```"):
        sql = "\n".join(
            line for line in sql.splitlines()
            if not line.startswith("```")
        ).strip()
    return {"sql": sql, "retry_count": state["retry_count"] + 1}


def node_build_chart(state: AgentState) -> dict:
    if not state["rows"]:
        return {"chart_config": {"should_chart": False}, "chart": None}

    columns = list(state["rows"][0].keys())
    messages = [
        {"role": "system", "content": CHART_SYSTEM},
        {"role": "user",   "content": chart_user_prompt(
            state["question"], columns, state["rows"][:5]
        )},
    ]
    raw = chat(messages).strip()
    try:
        config = json.loads(raw)
    except json.JSONDecodeError:
        config = {"should_chart": False}

    return {"chart_config": config, "chart": build_chart(config, state["rows"])}


def node_generate_insight(state: AgentState) -> dict:
    if not state["rows"]:
        insight = (
            "I was unable to retrieve data for your question. "
            "Please try rephrasing it or check that the data exists."
        )
        return {"insight": insight}

    messages = [
        {"role": "system", "content": INSIGHT_SYSTEM},
        {"role": "user",   "content": insight_user_prompt(
            state["question"], state["rows"][:20]
        )},
    ]
    return {"insight": chat(messages)}


# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_execute(state: AgentState) -> str:
    if state["error"]:
        if state["retry_count"] < 3:
            return "self_correct"
        return "generate_insight"   # graceful failure after 3 retries
    return "build_chart"


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(AgentState)

    g.add_node("get_schema",       node_get_schema)
    g.add_node("generate_sql",     node_generate_sql)
    g.add_node("execute_sql",      node_execute_sql)
    g.add_node("self_correct",     node_self_correct)
    g.add_node("build_chart",      node_build_chart)
    g.add_node("generate_insight", node_generate_insight)

    g.set_entry_point("get_schema")
    g.add_edge("get_schema",   "generate_sql")
    g.add_edge("generate_sql", "execute_sql")
    g.add_conditional_edges(
        "execute_sql",
        route_after_execute,
        {
            "self_correct":     "self_correct",
            "build_chart":      "build_chart",
            "generate_insight": "generate_insight",
        },
    )
    g.add_edge("self_correct",     "execute_sql")
    g.add_edge("build_chart",      "generate_insight")
    g.add_edge("generate_insight", END)

    return g.compile()


agent = build_graph()


def run_query(question: str) -> AgentState:
    initial_state: AgentState = {
        "question":    question,
        "schema":      "",
        "sql":         "",
        "rows":        [],
        "error":       None,
        "retry_count": 0,
        "chart_config": None,
        "chart":       None,
        "insight":     "",
    }
    return agent.invoke(initial_state)
