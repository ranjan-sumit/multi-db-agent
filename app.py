from __future__ import annotations

import inspect
import os
import subprocess
import sys
from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from src.agent import answer_question
from src.db_tools import DB_PATHS, get_table_profile


st.set_page_config(
    page_title="Retail Intelligence Agent",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


MICROSOFT_CSS = """
<style>
:root {
    --ms-blue: #0067b8;
    --ms-blue-dark: #004578;
    --ms-blue-soft: #eaf4ff;
    --ms-navy: #0f3a5f;
    --ms-gray-10: #f7f9fc;
    --ms-gray-20: #eef2f7;
    --ms-gray-30: #d8e0ea;
    --ms-gray-90: #46515f;
    --ms-gray-130: #1f2937;
    --ms-green: #107c10;
    --ms-orange: #ca5010;
    --ms-border: #e1dfdd;
    --ms-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
}

.stApp {
    background: linear-gradient(180deg, #f7fbff 0%, #f4f7fb 100%);
    color: var(--ms-gray-130);
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main {
    background: #f7f9fc !important;
    color: #1f2937 !important;
}

[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="stElementContainer"] {
    color: #1f2937 !important;
}

[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #b9c7d6;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
    color: #17212f !important;
}

[data-testid="stSidebarContent"] {
    background: #ffffff !important;
}

header[data-testid="stHeader"] {
    background: rgba(250, 249, 248, 0.96) !important;
    border-bottom: 1px solid var(--ms-border);
}

#MainMenu, footer {
    visibility: hidden;
}

.block-container {
    padding-top: 1.25rem;
    padding-bottom: 2.5rem;
    max-width: 1440px;
}

.ms-commandbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    background: linear-gradient(135deg, #ffffff 0%, #f3f9ff 100%);
    border: 1px solid #c8d7e6;
    border-radius: 4px;
    padding: 16px 18px;
    box-shadow: var(--ms-shadow);
    margin-bottom: 16px;
}

.ms-title {
    display: flex;
    align-items: center;
    gap: 12px;
}

.ms-app-icon {
    width: 42px;
    height: 42px;
    border-radius: 4px;
    background: linear-gradient(135deg, #005a9e, #00bcf2);
    display: grid;
    place-items: center;
    color: #ffffff;
    font-weight: 700;
    font-size: 15px;
}

.ms-title h1 {
    margin: 0;
    color: var(--ms-gray-130);
    font-size: 24px;
    line-height: 1.25;
    font-weight: 600;
    letter-spacing: 0;
}

.ms-title p {
    margin: 2px 0 0;
    color: #394b5f;
    font-size: 13px;
}

.ms-pill-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
}

.ms-pill {
    border: 1px solid #b7c7d8;
    background: #ffffff;
    color: var(--ms-gray-130);
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 12px;
    white-space: nowrap;
}

.ms-pill-blue {
    border-color: #75b6e7;
    color: #003e73;
    background: #dff0ff;
}

.ms-section-title {
    color: var(--ms-gray-130);
    font-size: 15px;
    font-weight: 600;
    margin: 18px 0 8px;
}

.ms-card {
    background: #ffffff;
    border: 1px solid var(--ms-border);
    border-radius: 4px;
    box-shadow: var(--ms-shadow);
    padding: 16px;
}

.metric-card {
    background: #ffffff;
    border: 1px solid #c8d7e6;
    border-top: 4px solid var(--ms-blue);
    border-radius: 4px;
    box-shadow: var(--ms-shadow);
    padding: 13px 14px;
    min-height: 86px;
}

.metric-label {
    color: #35465a;
    font-size: 12px;
    line-height: 1.2;
    margin-bottom: 7px;
}

.metric-value {
    color: #111827;
    font-size: 25px;
    line-height: 1.1;
    font-weight: 600;
}

.metric-sub {
    color: #526274;
    font-size: 11px;
    margin-top: 7px;
}

.answer-shell {
    background: #ffffff;
    border: 1px solid #c8d7e6;
    border-left: 6px solid var(--ms-blue);
    border-radius: 4px;
    box-shadow: var(--ms-shadow);
    padding: 16px 18px;
    margin-top: 8px;
}

.answer-title {
    color: var(--ms-gray-130);
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
}

.status-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
}

.status-chip {
    border-radius: 2px;
    background: #e8eef6;
    color: #1f2937;
    padding: 4px 8px;
    font-size: 12px;
}

.status-chip.good {
    background: #dff6dd;
    color: var(--ms-green);
}

.status-chip.warn {
    background: #fff4ce;
    color: var(--ms-orange);
}

.db-row {
    border: 1px solid #c2d1e1;
    border-radius: 4px;
    padding: 9px 10px;
    background: #ffffff;
    margin-bottom: 8px;
    display: grid;
    grid-template-columns: 30px 1fr;
    gap: 8px;
    align-items: start;
}

.db-icon {
    width: 28px;
    height: 28px;
    border-radius: 4px;
    display: grid;
    place-items: center;
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    background: #0067b8;
}

.db-icon.sales { background: #0067b8; }
.db-icon.detail { background: #107c10; }
.db-icon.product { background: #8764b8; }
.db-icon.store { background: #ca5010; }
.db-icon.calendar { background: #5c2d91; }

.sidebar-brand {
    background: linear-gradient(135deg, #004578, #0078d4);
    border: 1px solid #0b5cab;
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 12px;
}

.sidebar-brand-title {
    color: #ffffff;
    font-size: 18px;
    font-weight: 700;
    line-height: 1.2;
}

.sidebar-brand-sub {
    color: #dceeff;
    font-size: 12px;
    margin-top: 4px;
}

.db-name {
    color: #17212f;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0;
}

.db-path {
    color: #526274;
    font-size: 11px;
    word-break: break-all;
}

div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    border-radius: 4px;
    background: #ffffff !important;
    color: #1f2937 !important;
    border-color: #9db6ce !important;
}

div[data-testid="stTextInput"] input::placeholder {
    color: #64748b !important;
}

div.stButton > button {
    border-radius: 4px;
    border: 1px solid #b7c7d8;
    background: #ffffff;
    color: var(--ms-gray-130);
    font-weight: 400;
}

div.stButton > button:hover {
    border-color: var(--ms-blue);
    color: var(--ms-blue-dark);
    background: #eef7ff;
}

button[kind="primary"] {
    background: var(--ms-blue) !important;
    border-color: var(--ms-blue) !important;
    color: #ffffff !important;
}

[data-testid="stTabs"] button {
    color: var(--ms-gray-130) !important;
    background: #ffffff !important;
}

[data-testid="stTabs"] [role="tablist"] {
    background: #ffffff !important;
    border-bottom: 1px solid #c8d7e6;
}

[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #c8d7e6 !important;
    border-radius: 4px !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--ms-border);
    border-radius: 4px;
    overflow: hidden;
    background: #ffffff !important;
}

[data-testid="stAlert"] {
    background: #f3f9ff !important;
    color: #1f2937 !important;
}
</style>
"""


EXAMPLES = [
    "Compare summary TY sales vs detail net sales",
    "Sales by department",
    "Sales by region",
    "Sales by fiscal quarter",
    "Which price tier has the highest sales?",
    "Sales per square foot by trade area type",
    "Top 10 stores by net sales",
    "Top 5 SKUs by sales",
    "Show matching FW and store records across both databases",
    "Which stores exist in both databases?",
]


def initialize_databases() -> None:
    if all(path.exists() for path in DB_PATHS.values()):
        return
    subprocess.run([sys.executable, "setup_databases.py"], check=True)


@st.cache_data(ttl=300)
def load_profile() -> dict:
    return get_table_profile()


def fmt_int(value: object) -> str:
    try:
        return f"{int(float(value)):,}"
    except Exception:
        return "-"


def fmt_money(value: object) -> str:
    try:
        return f"${float(value):,.0f}"
    except Exception:
        return "-"


def metric_card(label: str, value: str, sub: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{escape(label)}</div>
            <div class="metric-value">{escape(value)}</div>
            <div class="metric-sub">{escape(sub)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_chart(df: pd.DataFrame | None) -> alt.Chart | None:
    if df is None or df.empty or len(df) < 2:
        return None

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        return None

    preferred_y = next((col for col in numeric_cols if any(key in col for key in ("sales", "margin", "cost"))), numeric_cols[0])
    label_cols = [col for col in df.columns if col not in numeric_cols]
    if not label_cols:
        return None

    x_col = label_cols[0]
    chart_df = df[[x_col, preferred_y]].copy().head(20)
    chart_df[preferred_y] = pd.to_numeric(chart_df[preferred_y], errors="coerce")
    chart_df = chart_df.dropna()
    if chart_df.empty:
        return None

    return (
        alt.Chart(chart_df)
        .mark_bar(color="#0078d4", cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            x=alt.X(f"{x_col}:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-30, labelColor="#605e5c")),
            y=alt.Y(f"{preferred_y}:Q", title=None, axis=alt.Axis(labelColor="#605e5c")),
            tooltip=[x_col, alt.Tooltip(preferred_y, format=",.2f")],
        )
        .properties(height=260)
        .configure_view(strokeWidth=0)
        .configure_axis(gridColor="#edebe9", domainColor="#e1dfdd")
    )


def render_database_list() -> None:
    icon_map = {
        "bobj": ("Σ", "sales"),
        "pbi": ("▦", "detail"),
        "product": ("P", "product"),
        "store": ("S", "store"),
        "calendar": ("C", "calendar"),
    }
    for source_name, db_path in DB_PATHS.items():
        icon_text, icon_class = icon_map.get(source_name, ("DB", "sales"))
        st.markdown(
            f"""
            <div class="db-row">
                <div class="db-icon {escape(icon_class)}">{escape(icon_text)}</div>
                <div>
                    <div class="db-name">{escape(source_name.upper())}</div>
                    <div class="db-path">{escape(str(db_path))}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.markdown(MICROSOFT_CSS, unsafe_allow_html=True)
initialize_databases()
profile = load_profile()

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">Retail Agent</div>
            <div class="sidebar-brand-sub">Local multi-database reporting</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### AI Settings")
    nvidia_key_set = bool(os.getenv("NVIDIA_API_KEY"))
    nvidia_api_key = st.text_input(
        "API key",
        value="",
        type="password",
        placeholder="Optional if NVIDIA_API_KEY is set",
    )
    llm_enabled = st.toggle("Use NVIDIA SQL agent", value=nvidia_key_set or bool(nvidia_api_key))

    model_options = [
        "openai/gpt-oss-120b",
        "nvidia/llama-3.3-70b-instruct",
        "meta/llama-3.1-70b-instruct",
        "mistralai/mixtral-8x22b-instruct-v0.1",
    ]
    selected_model = st.selectbox("Model", model_options, index=0)

    if nvidia_key_set or nvidia_api_key:
        st.success("NVIDIA key detected")
    else:
        st.info("Local rules active until a key is set")

    st.markdown("#### Data Sources")
    render_database_list()

    st.markdown("#### Example Questions")
    for example in EXAMPLES:
        if st.button(example, width="stretch"):
            st.session_state["question"] = example


mode_label = "NVIDIA SQL" if llm_enabled and (nvidia_key_set or nvidia_api_key) else "Local rules"
st.markdown(
    f"""
    <div class="ms-commandbar">
        <div class="ms-title">
            <div class="ms-app-icon">RI</div>
            <div>
                <h1>Retail Intelligence Agent</h1>
                <p>Microsoft-style reporting workspace across sales, product, store, and calendar databases</p>
            </div>
        </div>
        <div class="ms-pill-row">
            <span class="ms-pill ms-pill-blue">{escape(mode_label)}</span>
            <span class="ms-pill">5 databases</span>
            <span class="ms-pill">7 tables</span>
            <span class="ms-pill">SQLite local</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

sales_summary = profile["sales_summary"]
sales_detail = profile["sales_detail"]
product_master = profile["product_master"]
store_master = profile["store_master"]
calendar_profile = profile["calendar"]
coverage = profile["coverage"]

metric_cols = st.columns(6)
with metric_cols[0]:
    metric_card("TY net sales", fmt_money(sales_summary["ty_net_sales"]), "BOBJ summary")
with metric_cols[1]:
    metric_card("Detail sales", fmt_money(sales_detail["net_sales"]), "PBI detail")
with metric_cols[2]:
    metric_card("Detail rows", fmt_int(sales_detail["rows"]), "fact records")
with metric_cols[3]:
    metric_card("Product SKUs", fmt_int(product_master["hierarchy_skus"]), "product master")
with metric_cols[4]:
    metric_card("Stores", fmt_int(store_master["hierarchy_stores"]), "store master")
with metric_cols[5]:
    metric_card("Fiscal dates", fmt_int(calendar_profile["distinct_dates"]), "calendar")

st.markdown('<div class="ms-section-title">Ask The Agent</div>', unsafe_allow_html=True)
input_col, button_col = st.columns([6, 1])
with input_col:
    question = st.text_input(
        "Question",
        value=st.session_state.get("question", "Sales by region"),
        label_visibility="collapsed",
        placeholder="Ask about sales, margin, product, store, calendar, or reconciliation",
    )
with button_col:
    ask_clicked = st.button("Ask", type="primary", width="stretch")

answer_kwargs = {
    "use_llm": llm_enabled,
    "api_key": nvidia_api_key or None,
}
if "model" in inspect.signature(answer_question).parameters:
    answer_kwargs["model"] = selected_model

answer = answer_question(question, **answer_kwargs)
answer_mode = "NVIDIA LLM" if answer.llm_used else "Local rules"
answer_route = answer.route or "rules"
result_df = answer.combined

st.markdown(
    f"""
    <div class="answer-shell">
        <div class="answer-title">{escape(answer.title)}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(answer.answer.replace("$", "\\$"))

status_class = "good" if answer.llm_used else "warn"
st.markdown(
    f"""
    <div class="status-strip">
        <span class="status-chip {status_class}">Mode: {escape(answer_mode)}</span>
        <span class="status-chip">Path: {escape(answer_route)}</span>
        <span class="status-chip">Matched product rows: {fmt_int(coverage["detail_rows_with_product"])}</span>
        <span class="status-chip">Matched store rows: {fmt_int(coverage["detail_rows_with_store"])}</span>
        <span class="status-chip">Matched calendar rows: {fmt_int(coverage["detail_rows_with_calendar_date"])}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if answer.error:
    st.warning(f"NVIDIA path fell back to local rules: {answer.error}")

tabs = st.tabs(["Result", "Chart", "SQL", "Data Health"])

with tabs[0]:
    if result_df is not None and not result_df.empty:
        st.dataframe(result_df, width="stretch", hide_index=True)
    else:
        st.info("No result rows returned for this question.")

with tabs[1]:
    chart = build_chart(result_df)
    if chart is None:
        st.info("No chartable result for this answer.")
    else:
        st.altair_chart(chart, width="stretch")

with tabs[2]:
    if answer.llm_reasoning:
        with st.expander("Planning note", expanded=False):
            st.write(answer.llm_reasoning)

    if answer.results:
        for result in answer.results:
            with st.expander(f"{result.database.upper()} query", expanded=True):
                st.code(result.sql, language="sql")
                if not result.data.empty:
                    st.dataframe(result.data, width="stretch", hide_index=True)
    else:
        st.info("No SQL was executed.")

with tabs[3]:
    health_cols = st.columns(3)
    with health_cols[0]:
        metric_card("Product coverage", f'{fmt_int(coverage["detail_rows_with_product"])} / {fmt_int(sales_detail["rows"])}', "detail rows with SKU match")
    with health_cols[1]:
        metric_card("Store coverage", f'{fmt_int(coverage["detail_rows_with_store"])} / {fmt_int(sales_detail["rows"])}', "detail rows with store match")
    with health_cols[2]:
        metric_card("Calendar coverage", f'{fmt_int(coverage["detail_rows_with_calendar_date"])} / {fmt_int(sales_detail["rows"])}', "detail rows with date match")

    st.markdown('<div class="ms-section-title">Profile</div>', unsafe_allow_html=True)
    profile_rows = []
    for section, values in profile.items():
        for key, value in values.items():
            profile_rows.append({"source": section, "metric": key, "value": value})
    st.dataframe(pd.DataFrame(profile_rows), width="stretch", hide_index=True)


# from __future__ import annotations

# import os
# import inspect
# import subprocess
# import sys

# import streamlit as st

# from src.agent import answer_question
# from src.db_tools import BOBJ_DB, PBI_DB, get_table_profile


# st.set_page_config(page_title="Local Sales Agent", page_icon="DB", layout="wide")


# def initialize_databases() -> None:
#     if BOBJ_DB.exists() and PBI_DB.exists():
#         return
#     subprocess.run([sys.executable, "setup_databases.py"], check=True)


# initialize_databases()

# st.title("Local Two-Database Sales Agent")
# st.caption("A local Streamlit agent querying separate BOBJ-style and PBI-style SQLite databases.")

# with st.sidebar:
#     st.header("NVIDIA LLM")
#     nvidia_key_set = bool(os.getenv("NVIDIA_API_KEY"))
#     nvidia_api_key = st.text_input(
#         "NVIDIA API key",
#         value="",
#         type="password",
#         placeholder="Optional if NVIDIA_API_KEY is set",
#     )
#     llm_enabled = st.toggle("Use NVIDIA SQL agent", value=nvidia_key_set or bool(nvidia_api_key))
#     if nvidia_key_set or nvidia_api_key:
#         st.success("NVIDIA_API_KEY is set.")
#     else:
#         st.info("Set NVIDIA_API_KEY to enable the SQL agent.")

#     model_options = [
#         "openai/gpt-oss-120b",
#         "nvidia/llama-3.3-70b-instruct",
#         "meta/llama-3.1-70b-instruct",
#         "mistralai/mixtral-8x22b-instruct-v0.1",
#     ]
#     selected_model = st.selectbox(
#         "Model",
#         model_options,
#         index=0,
#         help="Used only when the NVIDIA SQL agent is enabled.",
#     )

#     st.header("Databases")
#     st.write("BOBJ summary")
#     st.code(str(BOBJ_DB), language="text")
#     st.write("PBI detail")
#     st.code(str(PBI_DB), language="text")

#     st.header("Try asking")
#     examples = [
#         "Compare summary TY sales vs detail net sales",
#         "What is total TY net sales?",
#         "What is total detail net sales?",
#         "Top 10 stores by net sales",
#         "Top 5 SKUs by sales",
#         "Show matching FW and store records across both databases",
#         "What is gross margin by store?",
#         "Which stores exist in both databases?",
#         "Compare TY sales and detail sales for matched FW/store pairs",
#         "Which date has the highest detail sales?",
#     ]
#     for example in examples:
#         if st.button(example, use_container_width=True):
#             st.session_state["question"] = example

# profile = get_table_profile()

# metric_cols = st.columns(4)
# metric_cols[0].metric("Summary rows", f"{int(profile['sales_summary']['rows']):,}")
# metric_cols[1].metric("Detail rows", f"{int(profile['sales_detail']['rows']):,}")
# metric_cols[2].metric("Summary stores", f"{int(profile['sales_summary']['distinct_stores']):,}")
# metric_cols[3].metric("Detail stores", f"{int(profile['sales_detail']['distinct_stores']):,}")

# question = st.text_input(
#     "Ask a question",
#     value=st.session_state.get("question", "Compare summary TY sales vs detail net sales"),
#     placeholder="Example: Which stores have the highest detail sales?",
# )

# answer_kwargs = {
#     "use_llm": llm_enabled,
#     "api_key": nvidia_api_key or None,
# }
# if "model" in inspect.signature(answer_question).parameters:
#     answer_kwargs["model"] = selected_model

# answer = answer_question(question, **answer_kwargs)

# st.subheader(answer.title)
# st.markdown(answer.answer.replace("$", "\\$"))

# if answer.error:
#     st.warning(f"NVIDIA path fell back to local rules: {answer.error}")

# status_cols = st.columns(2)
# status_cols[0].metric("Answer mode", "NVIDIA LLM" if answer.llm_used else "Local rules")
# status_cols[1].metric("Execution path", answer.route or "rules")

# if answer.llm_reasoning:
#     with st.expander("LLM planning note", expanded=False):
#         st.write(answer.llm_reasoning)

# if answer.combined is not None and not answer.combined.empty:
#     st.write("Combined result")
#     st.dataframe(answer.combined, use_container_width=True, hide_index=True)

# if answer.results:
#     st.write("Database queries")
#     for result in answer.results:
#         with st.expander(f"{result.database.upper()} query", expanded=False):
#             st.code(result.sql, language="sql")
#             st.dataframe(result.data, use_container_width=True, hide_index=True)

# with st.expander("Data profile", expanded=False):
#     st.json(profile)
