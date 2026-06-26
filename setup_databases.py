from pathlib import Path
import sqlite3

import pandas as pd


ROOT = Path(__file__).resolve().parent
SOURCE_XLSX = Path("/Users/divya/Downloads/BOBJ_PBI_Dummy_Final_7Tables_GraphReady.xlsx")

DATABASES = {
    "bobj": {
        "path": ROOT / "data" / "bobj" / "bobj_summary.db",
        "sheets": {"SALES SUMMARY_Dummy": "sales_summary"},
    },
    "pbi": {
        "path": ROOT / "data" / "pbi" / "pbi_detail.db",
        "sheets": {"SALES DETAIL_Dummy": "sales_detail"},
    },
    "product": {
        "path": ROOT / "data" / "product" / "product_master.db",
        "sheets": {
            "PRODUCT_HIERARCHY_Dummy": "product_hierarchy",
            "PRODUCT_PRICING_Dummy": "product_pricing",
        },
    },
    "store": {
        "path": ROOT / "data" / "store" / "store_master.db",
        "sheets": {
            "STORE_HIERARCHY_Dummy": "store_hierarchy",
            "STORE_LOCATION_Dummy": "store_location",
        },
    },
    "calendar": {
        "path": ROOT / "data" / "calendar" / "calendar.db",
        "sheets": {"FISCAL_CALENDAR_Dummy": "fiscal_calendar"},
    },
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]
    return df


def write_table(db_path: Path, table_name: str, df: pd.DataFrame) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)


def create_indexes() -> None:
    with sqlite3.connect(DATABASES["bobj"]["path"]) as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_summary_fw_store ON sales_summary (fw_id, store_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_summary_store ON sales_summary (store_id)")

    with sqlite3.connect(DATABASES["pbi"]["path"]) as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_detail_fw_store ON sales_detail (fw_id, store_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_detail_store ON sales_detail (store_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_detail_sku ON sales_detail (sku_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_detail_date ON sales_detail (date_id)")

    with sqlite3.connect(DATABASES["product"]["path"]) as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_product_hierarchy_sku ON product_hierarchy (sku_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_product_pricing_sku ON product_pricing (sku_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_product_department ON product_hierarchy (department)")

    with sqlite3.connect(DATABASES["store"]["path"]) as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_store_hierarchy_store ON store_hierarchy (store_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_store_location_store ON store_location (store_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_store_region ON store_hierarchy (region)")

    with sqlite3.connect(DATABASES["calendar"]["path"]) as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_calendar_date ON fiscal_calendar (date_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_calendar_fw ON fiscal_calendar (fw_id)")


def main() -> None:
    if not SOURCE_XLSX.exists():
        raise FileNotFoundError(f"Cannot find source workbook: {SOURCE_XLSX}")

    row_counts = {}
    for config in DATABASES.values():
        for sheet_name, table_name in config["sheets"].items():
            df = normalize_columns(pd.read_excel(SOURCE_XLSX, sheet_name=sheet_name))
            write_table(config["path"], table_name, df)
            row_counts[table_name] = len(df)

    create_indexes()

    for source_name, config in DATABASES.items():
        print(f"Created {source_name}: {config['path']}")
    for table_name, rows in row_counts.items():
        print(f"{table_name} rows: {rows:,}")


if __name__ == "__main__":
    main()


# from pathlib import Path
# import sqlite3

# import pandas as pd


# ROOT = Path(__file__).resolve().parent
# SOURCE_XLSX = Path("/Users/divya/Downloads/BOBJ-PBI_Dummy data.xlsx")
# BOBJ_DB = ROOT / "data" / "bobj" / "bobj_summary.db"
# PBI_DB = ROOT / "data" / "pbi" / "pbi_detail.db"


# def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
#     df = df.copy()
#     df.columns = [str(col).strip().lower() for col in df.columns]
#     return df


# def write_table(db_path: Path, table_name: str, df: pd.DataFrame) -> None:
#     db_path.parent.mkdir(parents=True, exist_ok=True)
#     with sqlite3.connect(db_path) as conn:
#         df.to_sql(table_name, conn, if_exists="replace", index=False)


# def create_indexes() -> None:
#     with sqlite3.connect(BOBJ_DB) as conn:
#         conn.execute("CREATE INDEX IF NOT EXISTS idx_summary_fw_store ON sales_summary (fw_id, store_id)")
#         conn.execute("CREATE INDEX IF NOT EXISTS idx_summary_store ON sales_summary (store_id)")

#     with sqlite3.connect(PBI_DB) as conn:
#         conn.execute("CREATE INDEX IF NOT EXISTS idx_detail_fw_store ON sales_detail (fw_id, store_id)")
#         conn.execute("CREATE INDEX IF NOT EXISTS idx_detail_store ON sales_detail (store_id)")
#         conn.execute("CREATE INDEX IF NOT EXISTS idx_detail_sku ON sales_detail (sku_id)")
#         conn.execute("CREATE INDEX IF NOT EXISTS idx_detail_date ON sales_detail (date_id)")


# def main() -> None:
#     if not SOURCE_XLSX.exists():
#         raise FileNotFoundError(f"Cannot find source workbook: {SOURCE_XLSX}")

#     summary = normalize_columns(pd.read_excel(SOURCE_XLSX, sheet_name="SALES SUMMARY_Dummy"))
#     detail = normalize_columns(pd.read_excel(SOURCE_XLSX, sheet_name="SALES DETAIL_Dummy"))

#     write_table(BOBJ_DB, "sales_summary", summary)
#     write_table(PBI_DB, "sales_detail", detail)
#     create_indexes()

#     print(f"Created {BOBJ_DB}")
#     print(f"Created {PBI_DB}")
#     print(f"sales_summary rows: {len(summary):,}")
#     print(f"sales_detail rows: {len(detail):,}")


# if __name__ == "__main__":
#     main()

