"""
download_data.py — Fetch UCI "Online Retail II", clean it, and write
data/online_retail_clean.csv (one row per line item, valid sales only).

The raw file is ~1M rows across two Excel sheets (Dec 2009 – Dec 2011). The
cleaned CSV is gitignored (too large to commit); this script reproduces it.

Cleaning: drop cancellations (invoice starting 'C'), non-positive quantity or
price, and rows with no Customer ID (can't be attributed to a customer);
add line revenue.
"""

import glob
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
OUT = DATA / "online_retail_clean.csv"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _xlsx_path() -> Path:
    hits = glob.glob(str(DATA / "raw" / "*.xlsx"))
    if hits:
        return Path(hits[0])
    zp = DATA / "online_retail_II.zip"
    if not zp.exists():
        print("downloading Online Retail II ...")
        urllib.request.urlretrieve(URL, zp)
    with zipfile.ZipFile(zp) as z:
        z.extractall(DATA / "raw")
    return Path(glob.glob(str(DATA / "raw" / "*.xlsx"))[0])


def main() -> int:
    xlsx = _xlsx_path()
    sheets = pd.read_excel(xlsx, sheet_name=None)
    df = pd.concat(sheets.values(), ignore_index=True)
    df = df.rename(columns={
        "Invoice": "invoice", "StockCode": "stock_code", "Description": "description",
        "Quantity": "quantity", "InvoiceDate": "invoice_date", "Price": "price",
        "Customer ID": "customer_id", "Country": "country",
    })

    df["invoice"] = df["invoice"].astype(str)
    df = df[~df["invoice"].str.startswith("C")]              # drop cancellations
    df = df[(df["quantity"] > 0) & (df["price"] > 0)]        # valid sales
    df = df.dropna(subset=["customer_id"])
    df["customer_id"] = df["customer_id"].astype(int)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["revenue"] = df["quantity"] * df["price"]

    df.to_csv(OUT, index=False)
    print(f"wrote {OUT.name}: {len(df):,} rows, "
          f"{df['customer_id'].nunique():,} customers, "
          f"{df['invoice_date'].min().date()}..{df['invoice_date'].max().date()}, "
          f"revenue GBP {df['revenue'].sum()/1e6:.1f}M")
    return 0


if __name__ == "__main__":
    sys.exit(main())
