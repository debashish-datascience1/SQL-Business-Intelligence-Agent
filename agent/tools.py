import os
import json
from sqlalchemy import create_engine, text, inspect
import plotly.graph_objects as go


def get_engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is not set in environment.")
    return create_engine(url)


# ── Schema introspection ──────────────────────────────────────────────────────

def fetch_schema() -> str:
    """Return a human-readable schema string for all tables in the database."""
    engine = get_engine()
    inspector = inspect(engine)
    lines = []

    for table in inspector.get_table_names():
        cols = inspector.get_columns(table)
        col_defs = ", ".join(
            f"{c['name']} ({str(c['type'])})" for c in cols
        )
        lines.append(f"{table}({col_defs})")

    return "\n".join(lines)


# ── SQL execution ─────────────────────────────────────────────────────────────

def execute_sql(sql: str) -> tuple[list[dict], str | None]:
    """
    Run a SQL query and return (rows, error).
    rows is a list of dicts on success; error is a string on failure.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            keys = list(result.keys())
            rows = [dict(zip(keys, row)) for row in result.fetchall()]
            return rows, None
    except Exception as e:
        return [], str(e)


# ── Chart building ────────────────────────────────────────────────────────────

def build_chart(chart_config: dict, rows: list[dict]) -> dict | None:
    """
    Build a Plotly figure from a chart config dict and query rows.
    Returns the figure as a JSON-serialisable dict, or None if charting is skipped.
    """
    if not chart_config.get("should_chart") or not rows:
        return None

    chart_type = chart_config.get("chart_type", "bar")
    x_col = chart_config.get("x")
    y_col = chart_config.get("y")
    title = chart_config.get("title", "")

    # Validate columns exist in results
    sample = rows[0]
    if x_col not in sample or y_col not in sample:
        return None

    x_vals = [r[x_col] for r in rows]
    y_vals = [r[y_col] for r in rows]

    if chart_type == "line":
        fig = go.Figure(go.Scatter(x=x_vals, y=y_vals, mode="lines+markers"))
    elif chart_type == "pie":
        fig = go.Figure(go.Pie(labels=x_vals, values=y_vals))
    else:
        fig = go.Figure(go.Bar(x=x_vals, y=y_vals))

    fig.update_layout(
        title=title,
        template="plotly_white",
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return json.loads(fig.to_json())


# ── Query history ─────────────────────────────────────────────────────────────

_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS query_history (
    id          SERIAL PRIMARY KEY,
    question    TEXT NOT NULL,
    sql         TEXT,
    row_count   INT,
    insight     TEXT,
    error       TEXT,
    retry_count INT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
)
"""


def log_query(
    question: str,
    sql: str,
    row_count: int,
    insight: str,
    error: str | None,
    retry_count: int,
) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(_HISTORY_DDL))
        conn.execute(
            text(
                """
                INSERT INTO query_history (question, sql, row_count, insight, error, retry_count)
                VALUES (:question, :sql, :row_count, :insight, :error, :retry_count)
                """
            ),
            {
                "question": question,
                "sql": sql,
                "row_count": row_count,
                "insight": insight,
                "error": error,
                "retry_count": retry_count,
            },
        )


def get_history(limit: int = 20) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT * FROM query_history ORDER BY created_at DESC LIMIT :limit"
            ),
            {"limit": limit},
        )
        keys = list(result.keys())
        return [dict(zip(keys, row)) for row in result.fetchall()]
