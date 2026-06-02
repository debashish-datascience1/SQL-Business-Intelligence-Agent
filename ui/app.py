import os
import requests
import streamlit as st
import plotly.graph_objects as go

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="SQL BI Agent",
    page_icon="📊",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📊 SQL BI Agent")
    st.markdown("Ask business questions in plain English. The agent writes the SQL, runs it, and explains the answer.")

    provider = st.selectbox(
        "LLM Provider",
        options=["groq", "openai"],
        help="Groq is free and fast. OpenAI (GPT-4o) gives slightly higher SQL quality.",
    )

    st.divider()
    st.markdown("**Example questions:**")
    examples = [
        "What is our MRR trend over the last 12 months?",
        "Which plan has the highest churn rate?",
        "Show me the top 10 companies by MRR",
        "How many new customers signed up each month in 2024?",
        "What percentage of revenue comes from each plan?",
        "Which industry has the most enterprise customers?",
        "Show me all overdue or failed invoices",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["prefill"] = ex

    st.divider()
    if st.button("Clear history", use_container_width=True):
        st.session_state["messages"] = []

# ── Chat history ──────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            _render_result(msg["content"]) if callable(globals().get("_render_result")) else st.write(msg["content"])


def _render_result(result: dict):
    """Render SQL, chart, insight, and raw data from an API response."""
    # Insight
    st.markdown(f"**Insight:** {result['insight']}")

    # Chart
    if result.get("chart"):
        fig = go.Figure(result["chart"])
        st.plotly_chart(fig, use_container_width=True)

    # SQL
    with st.expander("View SQL", expanded=False):
        st.code(result["sql"], language="sql")
        if result.get("retries", 0) > 0:
            st.caption(f"Self-corrected {result['retries']} time(s)")

    # Raw data
    if result.get("rows"):
        with st.expander(f"Raw data ({len(result['rows'])} rows)", expanded=False):
            st.dataframe(result["rows"], use_container_width=True)

    if result.get("error"):
        st.warning(f"Could not fully execute query after retries. Last error: {result['error']}")


# ── Input ─────────────────────────────────────────────────────────────────────

prefill = st.session_state.pop("prefill", "")
question = st.chat_input("Ask a business question...", key="chat_input") or prefill

if question:
    st.session_state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(
                    f"{API_URL}/query",
                    json={"question": question, "provider": provider},
                    timeout=60,
                )
                resp.raise_for_status()
                result = resp.json()
                _render_result(result)
                st.session_state["messages"].append({"role": "assistant", "content": result})
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach the API. Make sure the backend is running on port 8000.")
            except Exception as e:
                st.error(f"Error: {e}")
