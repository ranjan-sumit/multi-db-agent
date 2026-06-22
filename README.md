# Local Two-Database Sales Agent

This Streamlit app demonstrates a local agent that answers questions from two separate SQLite databases:

- `data/bobj/bobj_summary.db` with `sales_summary`
- `data/pbi/pbi_detail.db` with `sales_detail`

The databases are created from `/Users/divya/Downloads/BOBJ-PBI_Dummy data.xlsx`.

## Setup

```bash
cd /Users/divya/Documents/Codex/2026-06-22/files-mentioned-by-the-user-bobj/work/local_sales_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python setup_databases.py
streamlit run app.py
```

## NVIDIA API

The app can use NVIDIA's OpenAI-compatible API as a SQL agent. The model writes one read-only SQLite query against both attached local databases, the app validates the SQL, runs it locally, and asks the model to summarize the result.

```bash
export NVIDIA_API_KEY="your_key_here"
export NVIDIA_MODEL="openai/gpt-oss-120b"
streamlit run app.py
```

If `NVIDIA_API_KEY` is not set, the app still works using local deterministic rules.
You can also paste the key into the Streamlit sidebar for local demos.
The sidebar includes model selection; `openai/gpt-oss-120b` is the default.

## Example Questions

- What is total TY net sales?
- What is total detail net sales?
- Compare summary TY sales vs detail net sales.
- Which stores have the highest net sales?
- Show matching FW and store records across both databases.
- What is gross margin by store in detail?
