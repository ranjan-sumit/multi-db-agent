from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re

import pandas as pd

from src.db_tools import QueryResult, run_cross_database_query, run_query


@dataclass
class AgentAnswer:
    title: str
    answer: str
    results: list[QueryResult]
    combined: pd.DataFrame | None = None
    llm_used: bool = False
    llm_reasoning: str | None = None
    route: str | None = None
    error: str | None = None


SCHEMA_PROMPT = """
You are a senior sales analytics agent. You answer questions by writing one safe read-only SQLite query.

Databases are already attached:

1. bobj.sales_summary
   - fw_id TEXT
   - store_id INTEGER
   - ty_net_sales REAL
   - ly_net_sales REAL
   - ty_net_units INTEGER
   - ly_net_units INTEGER
   - ty_net_cost REAL
   - ly_net_cost REAL

2. pbi.sales_detail
   - date_id INTEGER, format YYYYMMDD
   - fw_id TEXT
   - store_id INTEGER
   - sku_id TEXT
   - net_sales REAL
   - net_units INTEGER
   - net_cost REAL

Business guidance:
- BOBJ summary is aggregated current-year/prior-year sales.
- PBI detail is transaction/SKU-level detail.
- Shared keys are fw_id and store_id, but this dummy data has sparse exact overlap.
- For cross-database reconciliation, aggregate before joining when needed.
- Use clear aliases.
- Add LIMIT 100 for detailed row lists.

Return only JSON with:
{
  "title": "short result title",
  "sql": "single SQLite SELECT/WITH query",
  "analysis_intent": "brief explanation of what the query will answer"
}

Never return INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, ATTACH, DETACH, PRAGMA, or multiple statements.
"""


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _number(value: float) -> str:
    return f"{value:,.0f}"


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def answer_question(
    question: str,
    use_llm: bool = True,
    api_key: str | None = None,
    model: str | None = None,
) -> AgentAnswer:
    if use_llm:
        llm_answer = _answer_with_nvidia_sql_agent(question, api_key=api_key, model=model)
        if llm_answer is not None:
            return llm_answer

    return answer_question_rules(question)


def answer_question_rules(question: str) -> AgentAnswer:
    q = question.lower().strip()

    if not q:
        return AgentAnswer(
            title="Ask a sales question",
            answer="Type a question about summary sales, detail sales, stores, SKUs, cost, margin, or matched records.",
            results=[],
        )

    if "exist in both" in q or "stores in both" in q:
        return stores_in_both_databases()

    if _contains_any(q, ("match", "matching", "join", "overlap", "both database", "both databases")):
        return matched_records()

    if "compare" in q or "vs" in q or "difference" in q:
        return compare_summary_and_detail()

    if "store" in q and _contains_any(q, ("highest", "top", "best", "rank")):
        return top_stores(q)

    if "sku" in q and _contains_any(q, ("highest", "top", "best", "rank")):
        return top_skus(q)

    if "date" in q and _contains_any(q, ("highest", "top", "best", "rank")):
        return top_dates(q)

    if "margin" in q or "profit" in q:
        return detail_margin_by_store(q)

    if "summary" in q or "ty" in q or "ly" in q:
        return summary_totals()

    if "detail" in q or "date" in q or "sku" in q:
        return detail_totals()

    if _contains_any(q, ("total", "sales", "unit", "cost")):
        return compare_summary_and_detail()

    return AgentAnswer(
        title="I need a more specific question",
        answer=(
            "I can answer questions about totals, comparisons, top stores, top SKUs, margins, "
            "and matched records across the two local databases."
        ),
        results=[],
    )


def _answer_with_nvidia_sql_agent(
    question: str,
    api_key: str | None = None,
    model: str | None = None,
) -> AgentAnswer | None:
    resolved_api_key = api_key or os.getenv("NVIDIA_API_KEY")
    if not resolved_api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=resolved_api_key,
        )
        selected_model = model or os.getenv("NVIDIA_MODEL", "openai/gpt-oss-120b")
        plan_completion = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": SCHEMA_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0,
            top_p=1,
            max_tokens=1200,
            stream=False,
        )
        plan_message = plan_completion.choices[0].message
        plan_content = plan_message.content or ""
        plan = _parse_json_payload(plan_content)
        sql = str(plan["sql"])
        title = str(plan.get("title") or "NVIDIA SQL answer")
        intent = str(plan.get("analysis_intent") or "")

        query_result = run_cross_database_query(sql)
        answer_text = _summarize_with_nvidia(
            client=client,
            model=selected_model,
            question=question,
            sql=query_result.sql,
            data=query_result.data,
        )
        reasoning = getattr(plan_message, "reasoning_content", None)
        return AgentAnswer(
            title=title,
            answer=answer_text,
            results=[query_result],
            combined=query_result.data,
            llm_used=True,
            llm_reasoning=reasoning or intent or plan_content,
            route="nvidia_sql",
        )
    except Exception as exc:
        fallback = answer_question_rules(question)
        fallback.llm_reasoning = f"NVIDIA LLM fallback used local rules because: {exc}"
        fallback.error = str(exc)
        return fallback


def _parse_json_payload(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.removeprefix("json").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    return json.loads(text)


def _summarize_with_nvidia(client, model: str, question: str, sql: str, data: pd.DataFrame) -> str:
    preview = data.head(50).to_dict(orient="records")
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You explain SQL query results for a business user. "
                    "Be concise, mention important numbers, and note limitations in the dummy data. "
                    "Do not invent values not present in the result."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "sql": sql,
                        "row_count": len(data),
                        "columns": list(data.columns),
                        "rows_preview": preview,
                    },
                    default=str,
                ),
            },
        ],
        temperature=0.2,
        top_p=1,
        max_tokens=700,
        stream=False,
    )
    return completion.choices[0].message.content or "I ran the query and returned the result table."


def summary_totals() -> AgentAnswer:
    result = run_query(
        "bobj",
        """
        SELECT
            SUM(ty_net_sales) AS ty_net_sales,
            SUM(ly_net_sales) AS ly_net_sales,
            SUM(ty_net_sales) - SUM(ly_net_sales) AS sales_variance,
            SUM(ty_net_units) AS ty_net_units,
            SUM(ly_net_units) AS ly_net_units,
            SUM(ty_net_cost) AS ty_net_cost,
            SUM(ly_net_cost) AS ly_net_cost
        FROM sales_summary
        """,
    )
    row = result.data.iloc[0]
    answer = (
        f"From the BOBJ summary database, TY net sales are {_money(row.ty_net_sales)} "
        f"versus LY net sales of {_money(row.ly_net_sales)}. "
        f"The sales variance is {_money(row.sales_variance)}. "
        f"TY units are {_number(row.ty_net_units)} and TY cost is {_money(row.ty_net_cost)}."
    )
    return AgentAnswer("Summary database totals", answer, [result])


def detail_totals() -> AgentAnswer:
    result = run_query(
        "pbi",
        """
        SELECT
            MIN(date_id) AS first_date_id,
            MAX(date_id) AS last_date_id,
            SUM(net_sales) AS net_sales,
            SUM(net_units) AS net_units,
            SUM(net_cost) AS net_cost,
            SUM(net_sales) - SUM(net_cost) AS gross_margin
        FROM sales_detail
        """,
    )
    row = result.data.iloc[0]
    answer = (
        f"From the PBI detail database, net sales are {_money(row.net_sales)} "
        f"across date IDs {int(row.first_date_id)} to {int(row.last_date_id)}. "
        f"Net units are {_number(row.net_units)}, net cost is {_money(row.net_cost)}, "
        f"and gross margin is {_money(row.gross_margin)}."
    )
    return AgentAnswer("Detail database totals", answer, [result])


def compare_summary_and_detail() -> AgentAnswer:
    summary = run_query(
        "bobj",
        """
        SELECT
            SUM(ty_net_sales) AS summary_ty_sales,
            SUM(ty_net_units) AS summary_ty_units,
            SUM(ty_net_cost) AS summary_ty_cost
        FROM sales_summary
        """,
    )
    detail = run_query(
        "pbi",
        """
        SELECT
            SUM(net_sales) AS detail_sales,
            SUM(net_units) AS detail_units,
            SUM(net_cost) AS detail_cost
        FROM sales_detail
        """,
    )
    combined = pd.concat([summary.data, detail.data], axis=1)
    row = combined.iloc[0]
    sales_diff = row.summary_ty_sales - row.detail_sales
    units_diff = row.summary_ty_units - row.detail_units
    cost_diff = row.summary_ty_cost - row.detail_cost
    answer = (
        f"BOBJ summary TY sales are {_money(row.summary_ty_sales)}, while PBI detail sales are "
        f"{_money(row.detail_sales)}. The difference is {_money(sales_diff)}. "
        f"Units differ by {_number(units_diff)} and cost differs by {_money(cost_diff)}. "
        "Because this dummy workbook has limited shared keys, this comparison is at total level."
    )
    return AgentAnswer("Cross-database comparison", answer, [summary, detail], combined)


def top_stores(question: str) -> AgentAnswer:
    limit = _extract_limit(question)
    result = run_query(
        "pbi",
        f"""
        SELECT
            store_id,
            SUM(net_sales) AS net_sales,
            SUM(net_units) AS net_units,
            SUM(net_cost) AS net_cost,
            SUM(net_sales) - SUM(net_cost) AS gross_margin
        FROM sales_detail
        GROUP BY store_id
        ORDER BY net_sales DESC
        LIMIT {limit}
        """,
    )
    top = result.data.iloc[0]
    answer = (
        f"The top store in the PBI detail database is store {int(top.store_id)} "
        f"with {_money(top.net_sales)} in net sales and {_number(top.net_units)} units."
    )
    return AgentAnswer(f"Top {limit} stores by detail sales", answer, [result], result.data)


def top_skus(question: str) -> AgentAnswer:
    limit = _extract_limit(question)
    result = run_query(
        "pbi",
        f"""
        SELECT
            sku_id,
            SUM(net_sales) AS net_sales,
            SUM(net_units) AS net_units,
            SUM(net_cost) AS net_cost,
            SUM(net_sales) - SUM(net_cost) AS gross_margin
        FROM sales_detail
        GROUP BY sku_id
        ORDER BY net_sales DESC
        LIMIT {limit}
        """,
    )
    top = result.data.iloc[0]
    answer = (
        f"The top SKU in the PBI detail database is {top.sku_id} "
        f"with {_money(top.net_sales)} in net sales."
    )
    return AgentAnswer(f"Top {limit} SKUs by detail sales", answer, [result], result.data)


def detail_margin_by_store(question: str) -> AgentAnswer:
    limit = _extract_limit(question)
    result = run_query(
        "pbi",
        f"""
        SELECT
            store_id,
            SUM(net_sales) AS net_sales,
            SUM(net_cost) AS net_cost,
            SUM(net_sales) - SUM(net_cost) AS gross_margin,
            CASE
                WHEN SUM(net_sales) = 0 THEN NULL
                ELSE (SUM(net_sales) - SUM(net_cost)) / SUM(net_sales)
            END AS gross_margin_rate
        FROM sales_detail
        GROUP BY store_id
        ORDER BY gross_margin DESC
        LIMIT {limit}
        """,
    )
    top = result.data.iloc[0]
    answer = (
        f"Store {int(top.store_id)} has the highest gross margin in the detail database: "
        f"{_money(top.gross_margin)} on {_money(top.net_sales)} of sales."
    )
    return AgentAnswer(f"Top {limit} stores by gross margin", answer, [result], result.data)


def top_dates(question: str) -> AgentAnswer:
    limit = _extract_limit(question)
    result = run_query(
        "pbi",
        f"""
        SELECT
            date_id,
            SUM(net_sales) AS net_sales,
            SUM(net_units) AS net_units,
            SUM(net_cost) AS net_cost,
            SUM(net_sales) - SUM(net_cost) AS gross_margin
        FROM sales_detail
        GROUP BY date_id
        ORDER BY net_sales DESC
        LIMIT {limit}
        """,
    )
    top = result.data.iloc[0]
    answer = (
        f"The highest detail-sales date is {int(top.date_id)} with "
        f"{_money(top.net_sales)} in net sales and {_number(top.net_units)} units."
    )
    return AgentAnswer(f"Top {limit} dates by detail sales", answer, [result], result.data)


def stores_in_both_databases() -> AgentAnswer:
    result = run_cross_database_query(
        """
        SELECT
            s.store_id,
            COUNT(DISTINCT s.fw_id) AS summary_fw_count,
            COUNT(DISTINCT d.fw_id) AS detail_fw_count
        FROM bobj.sales_summary s
        JOIN pbi.sales_detail d
            ON s.store_id = d.store_id
        GROUP BY s.store_id
        ORDER BY s.store_id
        LIMIT 100
        """
    )
    answer = (
        f"I found {len(result.data):,} stores that appear in both databases. "
        "This uses store overlap only, not exact FW/store matching."
    )
    return AgentAnswer("Stores appearing in both databases", answer, [result], result.data)


def matched_records() -> AgentAnswer:
    summary = run_query(
        "bobj",
        """
        SELECT
            fw_id,
            store_id,
            ty_net_sales,
            ty_net_units,
            ty_net_cost
        FROM sales_summary
        """,
    )
    detail = run_query(
        "pbi",
        """
        SELECT
            fw_id,
            store_id,
            SUM(net_sales) AS detail_sales,
            SUM(net_units) AS detail_units,
            SUM(net_cost) AS detail_cost
        FROM sales_detail
        GROUP BY fw_id, store_id
        """,
    )
    combined = summary.data.merge(detail.data, on=["fw_id", "store_id"], how="inner")
    if combined.empty:
        answer = "There are no exact `fw_id` and `store_id` matches between the two databases."
    else:
        combined["sales_difference"] = combined["ty_net_sales"] - combined["detail_sales"]
        answer = (
            f"I found {len(combined):,} exact `fw_id` + `store_id` match across the two databases. "
            "This confirms the local agent can query both places and combine results, but the dummy data has sparse overlap."
        )
    return AgentAnswer("Matched records across both databases", answer, [summary, detail], combined)


def _extract_limit(question: str) -> int:
    match = re.search(r"\btop\s+(\d+)\b|\b(\d+)\s+(?:stores|skus|sku)\b", question.lower())
    if not match:
        return 10
    value = next(group for group in match.groups() if group)
    return max(1, min(int(value), 50))
