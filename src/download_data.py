"""
download_data.py — Fetch UCI "Online Retail II", clean it, and write
data/online_retail_clean.csv (one row per line item, valid sales only).

The raw file is ~1M rows across two Excel sheets (Dec 2009 – Dec 2011). The
cleaned CSV is gitignored (too large to commit); this script reproduces it.

Cleaning:
- the yearly sheets overlap — UCI repeats 1–9 Dec 2010 in both — so those days
  are kept once, from the later sheet;
- cancellations (invoice starting 'C') are dropped together with the sale each
  one reverses: matched one-to-one on customer, stock code, quantity and unit
  price to the latest sale at or before the cancellation (partial cancellations
  aren't netted);
- non-positive quantity or price, and rows with no Customer ID (can't be
  attributed to a customer), are dropped; line revenue is added.
"""

import glob
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
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


def combine_sheets(sheets: dict) -> pd.DataFrame:
    """Stack the yearly sheets, trimming each to before the next one starts."""
    frames = list(sheets.values())
    kept = [f[f["InvoiceDate"] < nxt["InvoiceDate"].min()] for f, nxt in zip(frames, frames[1:])]
    return pd.concat(kept + frames[-1:], ignore_index=True)


def drop_cancelled_sales(sales: pd.DataFrame, cancels: pd.DataFrame) -> pd.DataFrame:
    """Remove each sale that a cancellation reverses (one sale per cancellation line)."""
    key = ["customer_id", "stock_code", "price", "qty"]
    c = cancels.assign(qty=-cancels["quantity"])[key + ["invoice_date"]]
    s = sales.assign(qty=sales["quantity"])[key + ["invoice_date"]]
    s = s[s.set_index(key).index.isin(c.set_index(key).index)]
    candidates = {k: g.sort_values("invoice_date") for k, g in s.groupby(key)}

    reversed_rows = []
    for k, cg in c.groupby(key):
        g = candidates.get(k)
        if g is None:
            continue
        dates, rows, used = g["invoice_date"].to_numpy(), g.index.to_numpy(), set()
        for when in np.sort(cg["invoice_date"].to_numpy()):
            for i in range(len(rows) - 1, -1, -1):      # latest unmatched sale at or before it
                if dates[i] <= when and rows[i] not in used:
                    used.add(rows[i])
                    break
        reversed_rows.extend(used)
    return sales.drop(index=reversed_rows)


def clean(raw: pd.DataFrame, stages: dict | None = None) -> pd.DataFrame:
    stages = {} if stages is None else stages
    df = raw.rename(columns={
        "Invoice": "invoice", "StockCode": "stock_code", "Description": "description",
        "Quantity": "quantity", "InvoiceDate": "invoice_date", "Price": "price",
        "Customer ID": "customer_id", "Country": "country",
    })
    stages["raw_rows"] = len(df)
    df["invoice"] = df["invoice"].astype(str)
    df["stock_code"] = df["stock_code"].astype(str).str.strip()

    is_cancel = df["invoice"].str.startswith("C")
    cancels = df[is_cancel & df["customer_id"].notna() & (df["quantity"] < 0)]
    df = df[~is_cancel]                                       # drop cancellations
    stages["after_dropping_cancellation_lines"] = len(df)
    df = df[(df["quantity"] > 0) & (df["price"] > 0)]         # valid sales
    stages["after_dropping_nonpositive_qty_or_price"] = len(df)
    df = df.dropna(subset=["customer_id"])
    stages["after_dropping_missing_customer_id"] = len(df)
    df = drop_cancelled_sales(df, cancels)                    # ...and the sales they reversed
    stages["after_dropping_cancelled_sales"] = len(df)

    df = df.copy()
    df["customer_id"] = df["customer_id"].astype(int)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["revenue"] = df["quantity"] * df["price"]
    return df


def main() -> int:
    xlsx = _xlsx_path()
    df = clean(combine_sheets(pd.read_excel(xlsx, sheet_name=None)))

    df.to_csv(OUT, index=False)
    print(f"wrote {OUT.name}: {len(df):,} rows, "
          f"{df['customer_id'].nunique():,} customers, "
          f"{df['invoice_date'].min().date()}..{df['invoice_date'].max().date()}, "
          f"revenue GBP {df['revenue'].sum()/1e6:.1f}M")
    return 0


if __name__ == "__main__":
    sys.exit(main())
