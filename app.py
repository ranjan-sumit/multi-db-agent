from __future__ import annotations

import os
import inspect
import subprocess
import sys

import streamlit as st

from src.agent import answer_question
from src.db_tools import BOBJ_DB, PBI_DB, get_table_profile


st.set_page_config(page_title="Local Sales Agent", page_icon="DB", layout="wide")


def initialize_databases() -> None:
    if BOBJ_DB.exists() and PBI_DB.exists():
        return
    subprocess.run([sys.executable, "setup_databases.py"], check=True)


initialize_databases()

st.title("Local Two-Database Sales Agent")
st.caption("A local Streamlit agent querying separate BOBJ-style and PBI-style SQLite databases.")

with st.sidebar:
    st.header("NVIDIA LLM")
    nvidia_key_set = bool(os.getenv("NVIDIA_API_KEY"))
    nvidia_api_key = st.text_input(
        "NVIDIA API key",
        value="",
        type="password",
        placeholder="Optional if NVIDIA_API_KEY is set",
    )
    llm_enabled = st.toggle("Use NVIDIA SQL agent", value=nvidia_key_set or bool(nvidia_api_key))
    if nvidia_key_set or nvidia_api_key:
        st.success("NVIDIA_API_KEY is set.")
    else:
        st.info("Set NVIDIA_API_KEY to enable the SQL agent.")

    model_options = [
        "openai/gpt-oss-120b",
        "nvidia/llama-3.3-70b-instruct",
        "meta/llama-3.1-70b-instruct",
        "mistralai/mixtral-8x22b-instruct-v0.1",
    ]
    selected_model = st.selectbox(
        "Model",
        model_options,
        index=0,
        help="Used only when the NVIDIA SQL agent is enabled.",
    )

    st.header("Databases")
    st.write("BOBJ summary")
    st.code(str(BOBJ_DB), language="text")
    st.write("PBI detail")
    st.code(str(PBI_DB), language="text")

    st.header("Try asking")
    examples = [
        "Compare summary TY sales vs detail net sales",
        "What is total TY net sales?",
        "What is total detail net sales?",
        "Top 10 stores by net sales",
        "Top 5 SKUs by sales",
        "Show matching FW and store records across both databases",
        "What is gross margin by store?",
        "Which stores exist in both databases?",
        "Compare TY sales and detail sales for matched FW/store pairs",
        "Which date has the highest detail sales?",
    ]
    for example in examples:
        if st.button(example, use_container_width=True):
            st.session_state["question"] = example

profile = get_table_profile()

metric_cols = st.columns(4)
metric_cols[0].metric("Summary rows", f"{int(profile['sales_summary']['rows']):,}")
metric_cols[1].metric("Detail rows", f"{int(profile['sales_detail']['rows']):,}")
metric_cols[2].metric("Summary stores", f"{int(profile['sales_summary']['distinct_stores']):,}")
metric_cols[3].metric("Detail stores", f"{int(profile['sales_detail']['distinct_stores']):,}")

question = st.text_input(
    "Ask a question",
    value=st.session_state.get("question", "Compare summary TY sales vs detail net sales"),
    placeholder="Example: Which stores have the highest detail sales?",
)

answer_kwargs = {
    "use_llm": llm_enabled,
    "api_key": nvidia_api_key or None,
}
if "model" in inspect.signature(answer_question).parameters:
    answer_kwargs["model"] = selected_model

answer = answer_question(question, **answer_kwargs)

st.subheader(answer.title)
st.markdown(answer.answer.replace("$", "\\$"))

if answer.error:
    st.warning(f"NVIDIA path fell back to local rules: {answer.error}")

status_cols = st.columns(2)
status_cols[0].metric("Answer mode", "NVIDIA LLM" if answer.llm_used else "Local rules")
status_cols[1].metric("Execution path", answer.route or "rules")

if answer.llm_reasoning:
    with st.expander("LLM planning note", expanded=False):
        st.write(answer.llm_reasoning)

if answer.combined is not None and not answer.combined.empty:
    st.write("Combined result")
    st.dataframe(answer.combined, use_container_width=True, hide_index=True)

if answer.results:
    st.write("Database queries")
    for result in answer.results:
        with st.expander(f"{result.database.upper()} query", expanded=False):
            st.code(result.sql, language="sql")
            st.dataframe(result.data, use_container_width=True, hide_index=True)

with st.expander("Data profile", expanded=False):
    st.json(profile)
