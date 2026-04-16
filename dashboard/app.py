"""
AutoAnalyst Dashboard — Streamlit UI for interacting with the agent.
Run: streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import get_settings

settings = get_settings()
API_URL = f"http://localhost:{settings.api_port}"


# ─── Page Config ─────────────────────────────────────────
st.set_page_config(
    page_title="AutoAnalyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Clean Light Theme CSS ───────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

    /* ── Global ── */
    .stApp {
        background-color: #FAFAFA;
        font-family: 'DM Sans', sans-serif;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E8E8E8;
    }
    section[data-testid="stSidebar"] .stMarkdown h2 {
        font-family: 'DM Sans', sans-serif;
        font-weight: 700;
        color: #1A1A1A;
        font-size: 1.1rem;
        letter-spacing: -0.02em;
    }
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        color: #444;
        font-size: 0.95rem;
    }

    /* ── Header ── */
    .main-header {
        font-family: 'DM Sans', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        color: #1A1A1A;
        letter-spacing: -0.03em;
        margin-bottom: 0;
        padding-bottom: 0;
    }
    .main-header span {
        background: linear-gradient(135deg, #2563EB, #7C3AED);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header {
        font-family: 'DM Sans', sans-serif;
        color: #888;
        font-size: 0.95rem;
        margin-top: 2px;
        margin-bottom: 1.5rem;
    }

    /* ── Chat messages ── */
    .stChatMessage {
        background-color: #FFFFFF !important;
        border: 1px solid #EBEBEB !important;
        border-radius: 12px !important;
        padding: 16px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }

    /* ── Step pipeline badges ── */
    .step-pipeline {
        display: flex;
        align-items: center;
        gap: 6px;
        flex-wrap: wrap;
        margin: 8px 0 12px 0;
    }
    .step-chip {
        display: inline-flex;
        align-items: center;
        padding: 4px 12px;
        border-radius: 20px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.75rem;
        font-weight: 500;
        background: #F0F4F8;
        color: #475569;
        border: 1px solid #E2E8F0;
    }
    .step-chip.done {
        background: #ECFDF5;
        color: #065F46;
        border-color: #A7F3D0;
    }
    .step-chip.error {
        background: #FEF2F2;
        color: #991B1B;
        border-color: #FECACA;
    }
    .step-arrow {
        color: #CBD5E1;
        font-size: 0.7rem;
    }

    /* ── Intent badge ── */
    .intent-bar {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 14px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        margin: 8px 0;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.85rem;
        color: #475569;
    }
    .intent-tag {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 6px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.78rem;
        font-weight: 500;
        background: #EEF2FF;
        color: #4338CA;
        border: 1px solid #C7D2FE;
    }

    /* ── SQL code block ── */
    .sql-label {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }

    /* ── Example prompt buttons ── */
    section[data-testid="stSidebar"] .stButton > button {
        background: #F8FAFC !important;
        color: #334155 !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        text-align: left !important;
        padding: 8px 12px !important;
        transition: all 0.15s ease !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: #EEF2FF !important;
        border-color: #C7D2FE !important;
        color: #4338CA !important;
    }

    /* ── Metrics ── */
    [data-testid="stMetric"] {
        background: #F8FAFC;
        border: 1px solid #E8E8E8;
        border-radius: 8px;
        padding: 12px 16px;
    }
    [data-testid="stMetricLabel"] {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.8rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    [data-testid="stMetricValue"] {
        font-family: 'DM Sans', sans-serif;
        font-weight: 700;
        color: #1E293B;
    }

    /* ── Expanders ── */
    .streamlit-expanderHeader {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        color: #334155 !important;
        background: #F8FAFC !important;
        border-radius: 8px !important;
    }

    /* ── Dataframe ── */
    .stDataFrame {
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        overflow: hidden;
    }

    /* ── Chat input ── */
    .stChatInput textarea {
        font-family: 'DM Sans', sans-serif !important;
        border-radius: 12px !important;
    }

    /* ── Dividers ── */
    hr {
        border-color: #F1F1F1 !important;
    }

    /* ── Status widget ── */
    [data-testid="stStatusWidget"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
    }

    /* ── Hide default streamlit branding ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    try:
        ds_resp = httpx.get(f"{API_URL}/datasets", timeout=10)
        datasets = ds_resp.json().get("datasets", [])
    except Exception:
        datasets = [settings.bq_dataset]

    selected_dataset = st.selectbox("Dataset", datasets, index=0)

    try:
        tbl_resp = httpx.get(f"{API_URL}/tables/{selected_dataset}", timeout=10)
        tables = tbl_resp.json().get("tables", [])
    except Exception:
        tables = []

    selected_table = st.selectbox(
        "Table",
        ["(auto-detect)"] + tables,
        index=0,
    )
    table_value = "" if selected_table == "(auto-detect)" else selected_table

    st.divider()
    st.markdown("### 📊 Table Info")
    if table_value and tables:
        try:
            schema_resp = httpx.get(
                f"{API_URL}/schema/{selected_dataset}/{table_value}",
                timeout=10,
            )
            schema_data = schema_resp.json()
            info = schema_data.get("info", {})

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Rows", f"{info.get('num_rows', '?'):,}")
            with col2:
                st.metric("Columns", info.get("num_columns", "?"))

            with st.expander("Schema"):
                for col in schema_data.get("schema", []):
                    mode_icon = "🔑" if col["mode"] == "REQUIRED" else "○"
                    st.markdown(
                        f"`{col['name']}` · {col['type'].lower()} {mode_icon}",
                    )
        except Exception:
            st.caption("Select a table to see its schema.")
    else:
        st.caption("Select a table above.")

    st.divider()
    st.markdown("### 💡 Try these")
    examples = [
        "Show me the top 10 rows",
        "Total sales by region",
        "Clean duplicates and fix nulls",
        "Statistical summary",
        "Bar chart of sales by category",
        "Delete cancelled orders",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex}", use_container_width=True):
            st.session_state["prompt_input"] = ex


# ─── Main Area ───────────────────────────────────────────
st.markdown('<p class="main-header">📊 <span>AutoAnalyst</span></p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Ask anything about your data in plain English.</p>', unsafe_allow_html=True)

# Chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def _render_chart(spec: dict, data: list[dict]):
    """Render a Plotly chart from the agent's chart specification."""
    if not data or not spec:
        return

    df = pd.DataFrame(data)
    chart_type = spec.get("chart_type", "bar")
    x = spec.get("x", "")
    y = spec.get("y", "")
    color = spec.get("color")
    title = spec.get("title", "Chart")
    labels = spec.get("labels", {})

    if color in ("null", "None", None):
        color = None

    # Light theme color palette
    light_colors = ["#6366F1", "#8B5CF6", "#EC4899", "#F59E0B", "#10B981", "#3B82F6", "#F97316", "#14B8A6"]

    chart_map = {
        "bar": px.bar,
        "line": px.line,
        "scatter": px.scatter,
        "pie": px.pie,
        "histogram": px.histogram,
        "heatmap": None,
    }

    try:
        if chart_type == "heatmap":
            fig = go.Figure(data=go.Heatmap(z=df.values, x=df.columns, y=df.index, colorscale="Blues"))
            fig.update_layout(title=title)
        elif chart_type == "pie":
            fig = px.pie(df, names=x, values=y, title=title, color_discrete_sequence=light_colors)
        elif chart_type in chart_map and chart_map[chart_type]:
            kwargs = {"x": x, "y": y, "title": title, "labels": labels, "color_discrete_sequence": light_colors}
            if color and color in df.columns:
                kwargs["color"] = color
            fig = chart_map[chart_type](df, **kwargs)
        else:
            fig = px.bar(df, x=x, y=y, title=title, color_discrete_sequence=light_colors)

        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans, sans-serif", color="#334155"),
            title_font=dict(size=16, color="#1E293B"),
            margin=dict(t=48, b=40, l=48, r=24),
            xaxis=dict(gridcolor="#F1F5F9", linecolor="#E2E8F0"),
            yaxis=dict(gridcolor="#F1F5F9", linecolor="#E2E8F0"),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not render chart: {e}")


# Display chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("data"):
            with st.expander("📋 Data", expanded=False):
                st.dataframe(pd.DataFrame(msg["data"]), use_container_width=True)
        if msg.get("chart_spec"):
            _render_chart(msg["chart_spec"], msg.get("data", []))


# ─── Chat Input ──────────────────────────────────────────
prompt = st.chat_input("Ask me anything about your data...")

if "prompt_input" in st.session_state:
    prompt = st.session_state.pop("prompt_input")

if prompt:
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("Working on it...", expanded=True) as status:
            try:
                response = httpx.post(
                    f"{API_URL}/agent/run",
                    json={
                        "prompt": prompt,
                        "dataset": selected_dataset,
                        "table": table_value,
                    },
                    timeout=120,
                )
                result = response.json()

                # Show step pipeline
                steps = result.get("steps", [])
                if steps:
                    chips = []
                    for i, s in enumerate(steps):
                        cls = "error" if "error" in s else "done"
                        chips.append(f'<span class="step-chip {cls}">{s}</span>')
                        if i < len(steps) - 1:
                            chips.append('<span class="step-arrow">▸</span>')
                    st.markdown(f'<div class="step-pipeline">{"".join(chips)}</div>', unsafe_allow_html=True)

                # Show intent + plan
                if result.get("intent"):
                    intent = result["intent"]
                    plan = result.get("plan", "")
                    st.markdown(
                        f'<div class="intent-bar">'
                        f'<span class="intent-tag">{intent}</span>'
                        f'<span>{plan}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                # Show SQL
                if result.get("sql"):
                    st.markdown('<p class="sql-label">Generated SQL</p>', unsafe_allow_html=True)
                    st.code(result["sql"], language="sql")

                status.update(label="✅ Complete", state="complete", expanded=False)

            except httpx.ConnectError:
                st.error("Cannot connect to the API server. Make sure it's running on port 8000.")
                result = {"response": "API server not available.", "data": [], "chart_spec": {}}
            except Exception as e:
                st.error(f"Error: {e}")
                result = {"response": str(e), "data": [], "chart_spec": {}}

        # Main response
        st.markdown(result.get("response", "No response."))

        # Data table
        data = result.get("data", [])
        if data:
            with st.expander(f"📋 Data  ·  {result.get('row_count', len(data))} rows", expanded=True):
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

        # Chart
        chart_spec = result.get("chart_spec", {})
        if chart_spec:
            _render_chart(chart_spec, data)

        # Cleaning report
        if result.get("cleaning_report"):
            with st.expander("🧹 Cleaning Report"):
                st.markdown(result["cleaning_report"])

        # Analysis
        if result.get("analysis"):
            with st.expander("📈 Analysis"):
                st.markdown(result["analysis"])

        # Save to history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": result.get("response", ""),
            "data": data[:20] if data else [],
            "chart_spec": chart_spec,
        })
