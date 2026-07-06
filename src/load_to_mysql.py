"""
load_to_mysql.py — Load the cleaned transactions CSV into MySQL `ecommerce`.
Optional: the Python analysis reads the CSV directly, so no DB is required.

Usage: python src/load_to_mysql.py
Env (optional): DB_HOST, DB_PORT, DB_USER, DB_PASSWORD (defaults: root@localhost)
"""

import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).parent.parent
CSV = ROOT / "data" / "online_retail_clean.csv"


def get_engine():
    user, pwd = os.environ.get("DB_USER", "root"), os.environ.get("DB_PASSWORD", "")
    host, port = os.environ.get("DB_HOST", "localhost"), os.environ.get("DB_PORT", "3306")
    return create_engine(
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(pwd)}@{host}:{port}"
        f"/ecommerce?charset=utf8mb4")


def main() -> int:
    df = pd.read_csv(CSV, parse_dates=["invoice_date"])
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(text("TRUNCATE TABLE transactions"))
    df.to_sql("transactions", eng, if_exists="append", index=False, chunksize=10000)
    with eng.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
    print(f"loaded transactions={n:,}")
    return 0 if n == len(df) else 1


if __name__ == "__main__":
    sys.exit(main())
