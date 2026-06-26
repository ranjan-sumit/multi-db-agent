# from __future__ import annotations

# from dataclasses import dataclass
# from pathlib import Path
# import re
# import sqlite3
# import subprocess
# import sys

# import pandas as pd


# ROOT = Path(__file__).resolve().parents[1]
# BOBJ_DB = ROOT / "data" / "bobj" / "bobj_summary.db"
# PBI_DB = ROOT / "data" / "pbi" / "pbi_detail.db"


# @dataclass(frozen=True)
# class QueryResult:
#     database: str
#     sql: str
#     data: pd.DataFrame


# def ensure_databases_exist() -> None:
#     if BOBJ_DB.exists() and PBI_DB.exists():
#         return

#     setup_script = ROOT / "setup_databases.py"
#     if setup_script.exists():
#         subprocess.run([sys.executable, str(setup_script)], cwd=ROOT, check=True)
#         if BOBJ_DB.exists() and PBI_DB.exists():
#             return

#     missing = [str(path) for path in (BOBJ_DB, PBI_DB) if not path.exists()]
#     raise FileNotFoundError(
#         "Database files are missing. Run `python setup_databases.py` first. Missing: "
#         + ", ".join(missing)
#     )


# def run_query(database: str, sql: str, params: tuple = ()) -> QueryResult:
#     ensure_databases_exist()
#     db_path = {"bobj": BOBJ_DB, "pbi": PBI_DB}[database]
#     with sqlite3.connect(db_path) as conn:
#         df = pd.read_sql_query(sql, conn, params=params)
#     return QueryResult(database=database, sql=sql.strip(), data=df)


# def run_cross_database_query(sql: str) -> QueryResult:
#     ensure_databases_exist()
#     safe_sql = validate_read_only_sql(sql)
#     with sqlite3.connect(":memory:") as conn:
#         conn.execute(f"ATTACH DATABASE '{BOBJ_DB}' AS bobj")
#         conn.execute(f"ATTACH DATABASE '{PBI_DB}' AS pbi")
#         df = pd.read_sql_query(safe_sql, conn)
#     return QueryResult(database="cross-db", sql=safe_sql, data=df)


# def validate_read_only_sql(sql: str) -> str:
#     cleaned = sql.strip()
#     cleaned = re.sub(r"^```(?:sql)?", "", cleaned, flags=re.IGNORECASE).strip()
#     cleaned = re.sub(r"```$", "", cleaned).strip()
#     cleaned = cleaned.rstrip(";").strip()

#     if not cleaned:
#         raise ValueError("SQL is empty.")

#     lowered = _strip_sql_comments(cleaned).lower()
#     if not (lowered.startswith("select") or lowered.startswith("with")):
#         raise ValueError("Only SELECT or WITH queries are allowed.")

#     blocked = (
#         "attach",
#         "analyze",
#         "begin",
#         "commit",
#         "copy",
#         "detach",
#         "insert",
#         "update",
#         "delete",
#         "drop",
#         "alter",
#         "create",
#         "load_extension",
#         "reindex",
#         "release",
#         "replace",
#         "rollback",
#         "savepoint",
#         "truncate",
#         "pragma",
#         "vacuum",
#     )
#     if re.search(r"\b(" + "|".join(blocked) + r")\b", lowered):
#         raise ValueError("Only read-only analytics queries are allowed.")

#     if ";" in cleaned:
#         raise ValueError("Only one SQL statement is allowed.")

#     return cleaned


# def _strip_sql_comments(sql: str) -> str:
#     sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
#     sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
#     return sql.strip()


# def get_table_profile() -> dict:
#     summary = run_query(
#         "bobj",
#         """
#         SELECT
#             COUNT(*) AS rows,
#             COUNT(DISTINCT fw_id) AS distinct_fw_ids,
#             COUNT(DISTINCT store_id) AS distinct_stores,
#             SUM(ty_net_sales) AS ty_net_sales,
#             SUM(ly_net_sales) AS ly_net_sales,
#             SUM(ty_net_units) AS ty_net_units,
#             SUM(ly_net_units) AS ly_net_units,
#             SUM(ty_net_cost) AS ty_net_cost,
#             SUM(ly_net_cost) AS ly_net_cost
#         FROM sales_summary
#         """,
#     ).data.iloc[0].to_dict()

#     detail = run_query(
#         "pbi",
#         """
#         SELECT
#             COUNT(*) AS rows,
#             COUNT(DISTINCT fw_id) AS distinct_fw_ids,
#             COUNT(DISTINCT store_id) AS distinct_stores,
#             COUNT(DISTINCT sku_id) AS distinct_skus,
#             MIN(date_id) AS min_date_id,
#             MAX(date_id) AS max_date_id,
#             SUM(net_sales) AS net_sales,
#             SUM(net_units) AS net_units,
#             SUM(net_cost) AS net_cost
#         FROM sales_detail
#         """,
#     ).data.iloc[0].to_dict()

#     return {"sales_summary": summary, "sales_detail": detail}

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB_PATHS = {
    "bobj": ROOT / "data" / "bobj" / "bobj_summary.db",
    "pbi": ROOT / "data" / "pbi" / "pbi_detail.db",
    "product": ROOT / "data" / "product" / "product_master.db",
    "store": ROOT / "data" / "store" / "store_master.db",
    "calendar": ROOT / "data" / "calendar" / "calendar.db",
}
BOBJ_DB = DB_PATHS["bobj"]
PBI_DB = DB_PATHS["pbi"]
PRODUCT_DB = DB_PATHS["product"]
STORE_DB = DB_PATHS["store"]
CALENDAR_DB = DB_PATHS["calendar"]


@dataclass(frozen=True)
class QueryResult:
    database: str
    sql: str
    data: pd.DataFrame


def ensure_databases_exist() -> None:
    if all(path.exists() for path in DB_PATHS.values()):
        return

    setup_script = ROOT / "setup_databases.py"
    if setup_script.exists():
        subprocess.run([sys.executable, str(setup_script)], cwd=ROOT, check=True)
        if all(path.exists() for path in DB_PATHS.values()):
            return

    missing = [str(path) for path in DB_PATHS.values() if not path.exists()]
    raise FileNotFoundError(
        "Database files are missing. Run `python setup_databases.py` first. Missing: "
        + ", ".join(missing)
    )


def run_query(database: str, sql: str, params: tuple = ()) -> QueryResult:
    ensure_databases_exist()
    db_path = DB_PATHS[database]
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    return QueryResult(database=database, sql=sql.strip(), data=df)


def run_cross_database_query(sql: str) -> QueryResult:
    ensure_databases_exist()
    safe_sql = validate_read_only_sql(sql)
    with sqlite3.connect(":memory:") as conn:
        for alias, db_path in DB_PATHS.items():
            conn.execute(f"ATTACH DATABASE '{db_path}' AS {alias}")
        df = pd.read_sql_query(safe_sql, conn)
    return QueryResult(database="cross-db", sql=safe_sql, data=df)


def validate_read_only_sql(sql: str) -> str:
    cleaned = sql.strip()
    cleaned = re.sub(r"^```(?:sql)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    cleaned = cleaned.rstrip(";").strip()

    if not cleaned:
        raise ValueError("SQL is empty.")

    lowered = _strip_sql_comments(cleaned).lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("Only SELECT or WITH queries are allowed.")

    blocked = (
        "attach",
        "analyze",
        "begin",
        "commit",
        "copy",
        "detach",
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "load_extension",
        "reindex",
        "release",
        "replace",
        "rollback",
        "savepoint",
        "truncate",
        "pragma",
        "vacuum",
    )
    if re.search(r"\b(" + "|".join(blocked) + r")\b", lowered):
        raise ValueError("Only read-only analytics queries are allowed.")

    if ";" in cleaned:
        raise ValueError("Only one SQL statement is allowed.")

    return cleaned


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql.strip()


def get_table_profile() -> dict:
    summary = run_query(
        "bobj",
        """
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT fw_id) AS distinct_fw_ids,
            COUNT(DISTINCT store_id) AS distinct_stores,
            SUM(ty_net_sales) AS ty_net_sales,
            SUM(ly_net_sales) AS ly_net_sales,
            SUM(ty_net_units) AS ty_net_units,
            SUM(ly_net_units) AS ly_net_units,
            SUM(ty_net_cost) AS ty_net_cost,
            SUM(ly_net_cost) AS ly_net_cost
        FROM sales_summary
        """,
    ).data.iloc[0].to_dict()

    detail = run_query(
        "pbi",
        """
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT fw_id) AS distinct_fw_ids,
            COUNT(DISTINCT store_id) AS distinct_stores,
            COUNT(DISTINCT sku_id) AS distinct_skus,
            MIN(date_id) AS min_date_id,
            MAX(date_id) AS max_date_id,
            SUM(net_sales) AS net_sales,
            SUM(net_units) AS net_units,
            SUM(net_cost) AS net_cost
        FROM sales_detail
        """,
    ).data.iloc[0].to_dict()

    product = run_query(
        "product",
        """
        SELECT
            (SELECT COUNT(*) FROM product_hierarchy) AS hierarchy_rows,
            (SELECT COUNT(DISTINCT sku_id) FROM product_hierarchy) AS hierarchy_skus,
            (SELECT COUNT(DISTINCT department) FROM product_hierarchy) AS departments,
            (SELECT COUNT(*) FROM product_pricing) AS pricing_rows,
            (SELECT COUNT(DISTINCT sku_id) FROM product_pricing) AS pricing_skus
        """,
    ).data.iloc[0].to_dict()

    store = run_query(
        "store",
        """
        SELECT
            (SELECT COUNT(*) FROM store_hierarchy) AS hierarchy_rows,
            (SELECT COUNT(DISTINCT store_id) FROM store_hierarchy) AS hierarchy_stores,
            (SELECT COUNT(DISTINCT zone) FROM store_hierarchy) AS zones,
            (SELECT COUNT(DISTINCT region) FROM store_hierarchy) AS regions,
            (SELECT COUNT(*) FROM store_location) AS location_rows,
            (SELECT COUNT(DISTINCT store_id) FROM store_location) AS location_stores
        """,
    ).data.iloc[0].to_dict()

    calendar = run_query(
        "calendar",
        """
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT date_id) AS distinct_dates,
            COUNT(DISTINCT fw_id) AS distinct_fw_ids,
            COUNT(DISTINCT fiscal_year) AS fiscal_years,
            MIN(date_id) AS min_date_id,
            MAX(date_id) AS max_date_id
        FROM fiscal_calendar
        """,
    ).data.iloc[0].to_dict()

    coverage = run_cross_database_query(
        """
        SELECT
            (SELECT COUNT(*) FROM pbi.sales_detail d JOIN product.product_hierarchy ph ON d.sku_id = ph.sku_id) AS detail_rows_with_product,
            (SELECT COUNT(*) FROM pbi.sales_detail d JOIN product.product_pricing pp ON d.sku_id = pp.sku_id) AS detail_rows_with_pricing,
            (SELECT COUNT(*) FROM pbi.sales_detail d JOIN store.store_hierarchy sh ON d.store_id = sh.store_id) AS detail_rows_with_store,
            (SELECT COUNT(*) FROM pbi.sales_detail d JOIN store.store_location sl ON d.store_id = sl.store_id) AS detail_rows_with_location,
            (SELECT COUNT(*) FROM pbi.sales_detail d JOIN calendar.fiscal_calendar fc ON d.date_id = fc.date_id) AS detail_rows_with_calendar_date,
            (SELECT COUNT(*) FROM bobj.sales_summary s JOIN pbi.sales_detail d ON s.fw_id = d.fw_id AND s.store_id = d.store_id) AS exact_summary_detail_matches
        """
    ).data.iloc[0].to_dict()

    return {
        "sales_summary": summary,
        "sales_detail": detail,
        "product_master": product,
        "store_master": store,
        "calendar": calendar,
        "coverage": coverage,
    }

