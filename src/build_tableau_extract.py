"""
build_tableau_extract.py — One flat, Tableau-ready table for the Tableau Public
dashboard, plus the numbers that dashboard has to reproduce.

One row per sales line (same cleaning as download_data.py), with one product
name per stock code, a Product / Non-product flag (postage, fees, vouchers and
manual adjustments aren't SKUs, so they'd distort SKU concentration) and each
customer's RFM segment joined on. Writes data/tableau/retail_sales_lines.csv
and data/tableau/checkpoints.json — totals, segment shares, cohort retention
and SKU concentration to check the Tableau build against.
"""

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from prep import load, customer_rfm, cohort_retention, ROOT  # noqa: E402

OUT = ROOT / "data" / "tableau"
NON_PRODUCT = {"POST", "DOT", "C2", "M", "BANK CHARGES", "AMAZONFEE", "ADJUST",
               "ADJUST2", "B", "D", "CRUK", "S", "PADS", "TEST001", "TEST002"}


def is_product(code: pd.Series) -> pd.Series:
    upper = code.str.upper()
    return ~(upper.isin(NON_PRODUCT) | upper.str.startswith("GIFT_"))


def sales_lines(df: pd.DataFrame, rfm: pd.DataFrame) -> pd.DataFrame:
    code = df["stock_code"].astype(str).str.strip()
    desc = (df["description"].fillna("").astype(str).str.strip()
              .str.replace(r"\s+", " ", regex=True))
    # descriptions drift over two years; keep the most common one per code
    named = pd.DataFrame({"code": code, "name": desc})
    names = (named[named["name"] != ""].value_counts().reset_index()
               .drop_duplicates("code").set_index("code")["name"])
    return pd.DataFrame({
        "Order ID": df["invoice"].astype(str),
        "Order Date": df["invoice_date"].dt.strftime("%Y-%m-%d"),
        "Customer ID": df["customer_id"].astype(int),
        "Country": df["country"],
        "Stock Code": code,
        "Product": code.map(names).fillna(code),
        "Line Type": np.where(is_product(code), "Product", "Non-product"),
        "Units": df["quantity"].astype(int),
        "Revenue": df["revenue"].round(2),
        "Customer Segment": df["customer_id"].map(rfm.set_index("customer_id")["segment"]),
    })


def checkpoints(df: pd.DataFrame, lines: pd.DataFrame, rfm: pd.DataFrame) -> dict:
    pct = lambda x: round(float(x), 1)  # noqa: E731
    rev = lines["Revenue"].sum()
    n_orders = lines["Order ID"].nunique()
    orders_per_customer = lines.groupby("Customer ID")["Order ID"].nunique()
    monthly = lines.groupby(lines["Order Date"].str[:7])["Revenue"].sum()
    country = lines.groupby("Country")["Revenue"].sum().sort_values(ascending=False)
    seg = (lines.groupby("Customer Segment")
                .agg(customers=("Customer ID", "nunique"), revenue=("Revenue", "sum"))
                .sort_values("revenue", ascending=False))

    ret = cohort_retention(df)
    cohort_sizes = df.groupby("customer_id")["invoice_month"].min().value_counts().sort_index()

    cust = rfm["monetary"].sort_values(ascending=False).reset_index(drop=True)
    cust_cum = cust.cumsum() / cust.sum() * 100
    sku = (lines[lines["Line Type"] == "Product"]
             .groupby(["Stock Code", "Product"])["Revenue"].sum().sort_values(ascending=False))
    sku_cum = sku.cumsum() / sku.sum() * 100

    return {
        "rows": len(lines),
        "revenue_gbp": round(float(rev), 2),
        "orders": int(n_orders),
        "customers": int(lines["Customer ID"].nunique()),
        "units": int(lines["Units"].sum()),
        "aov_gbp": round(float(rev / n_orders), 2),
        "repeat_customer_pct": pct((orders_per_customer > 1).mean() * 100),
        "date_range": [lines["Order Date"].min(), lines["Order Date"].max()],
        "revenue_by_year_gbp": {y: round(float(v)) for y, v in monthly.groupby(monthly.index.str[:4]).sum().items()},
        "peak_month": {"month": monthly.idxmax(), "revenue_gbp": round(float(monthly.max()))},
        "countries": int(lines["Country"].nunique()),
        "uk_revenue_pct": pct(country.get("United Kingdom", 0) / rev * 100),
        "international": {
            "revenue_gbp": round(float(lines.loc[lines["Country"] != "United Kingdom", "Revenue"].sum())),
            "orders": int(lines.loc[lines["Country"] != "United Kingdom", "Order ID"].nunique()),
            "customers": int(lines.loc[lines["Country"] != "United Kingdom", "Customer ID"].nunique()),
        },
        "top_international_gbp": {c: round(float(v)) for c, v in country.drop("United Kingdom", errors="ignore").head(5).items()},
        "segments": {s: {"customers_pct": pct(r["customers"] / len(rfm) * 100),
                         "revenue_pct": pct(r["revenue"] / rev * 100)} for s, r in seg.iterrows()},
        "top20pct_customers_revenue_pct": pct(cust_cum.iloc[int(len(cust_cum) * 0.2)]),
        "cohort_month1_avg_pct": pct(ret.iloc[:, 1].mean()),
        "cohort_month6_avg_pct": pct(ret.iloc[:, 6].mean()),
        "first_cohort": {"cohort": ret.index[0], "customers": int(cohort_sizes.iloc[0]),
                         "month1_pct": pct(ret.iloc[0, 1]), "month12_pct": pct(ret.iloc[0, 12])},
        "product_skus": int(len(sku)),
        "top20pct_skus_revenue_pct": pct(sku_cum.iloc[int(len(sku_cum) * 0.2)]),
        "top_skus_gbp": {f"{c} {p}": round(float(v)) for (c, p), v in sku.head(5).items()},
        "non_product_revenue_pct": pct(lines.loc[lines["Line Type"] != "Product", "Revenue"].sum() / rev * 100),
    }


def write(df: pd.DataFrame) -> dict:
    rfm = customer_rfm(df)
    lines = sales_lines(df, rfm)
    OUT.mkdir(parents=True, exist_ok=True)
    lines.to_csv(OUT / "retail_sales_lines.csv", index=False)
    cp = checkpoints(df, lines, rfm)
    (OUT / "checkpoints.json").write_text(json.dumps(cp, indent=2), encoding="utf-8")
    return cp


def main() -> int:
    cp = write(load())
    print(json.dumps(cp, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
