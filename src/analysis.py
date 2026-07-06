"""
analysis.py — Growth analytics: cohort retention, RFM segmentation, and the
revenue concentration (Pareto) that tells you where to spend retention budget.

Writes figures + reports/growth_summary.md + dashboard-ready CSVs the Streamlit
app / a Tableau workbook reads.
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sys.path.insert(0, str(Path(__file__).parent))
from prep import load, customer_rfm, cohort_retention, ROOT  # noqa: E402

FIG = ROOT / "reports" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
OUTD = ROOT / "reports"


def main():
    df = load()
    out = ["# Growth analytics — Online Retail II", ""]
    out.append(f"- Transactions: **{len(df):,}** · customers: **{df['customer_id'].nunique():,}** "
               f"· revenue: **GBP {df['revenue'].sum()/1e6:.1f}M** "
               f"({df['invoice_date'].min().date()} to {df['invoice_date'].max().date()})")
    out.append("")

    # ── 1. cohort retention ──────────────────────────────────────────────────
    ret = cohort_retention(df)
    ret.to_csv(OUTD / "cohort_retention.csv")
    plt.figure(figsize=(12, 8))
    sns.heatmap(ret.iloc[:, :13], annot=True, fmt=".0f", cmap="crest",
                cbar_kws={"label": "% of cohort still active"})
    plt.xlabel("Months since first purchase")
    plt.ylabel("Acquisition cohort")
    plt.title("Monthly cohort retention (%)")
    plt.tight_layout()
    plt.savefig(FIG / "cohort_retention_heatmap.png", dpi=150)
    plt.close()
    m1 = ret.iloc[:, 1].mean()
    m6 = ret.iloc[:, 6].mean() if ret.shape[1] > 6 else float("nan")
    out.append(f"- **Retention is the core problem:** on average only **{m1:.0f}%** of a "
               f"cohort returns the month after acquisition, ~{m6:.0f}% by month 6. "
               f"Acquisition without retention leaks revenue.")

    # ── 2. RFM segmentation ──────────────────────────────────────────────────
    rfm = customer_rfm(df)
    seg = rfm.groupby("segment").agg(
        customers=("customer_id", "size"),
        revenue=("monetary", "sum"),
        avg_value=("monetary", "mean"),
    ).sort_values("revenue", ascending=False)
    seg["pct_customers"] = (seg["customers"] / seg["customers"].sum() * 100).round(1)
    seg["pct_revenue"] = (seg["revenue"] / seg["revenue"].sum() * 100).round(1)
    seg.to_csv(OUTD / "rfm_segments.csv")

    plt.figure(figsize=(10, 6))
    ax = seg.sort_values("revenue")["revenue"].div(1e6).plot(kind="barh", color="#2a9d8f")
    plt.xlabel("Revenue (GBP M)")
    plt.title("Revenue by RFM segment")
    for i, (c, r) in enumerate(zip(seg.sort_values("revenue")["pct_customers"],
                                   seg.sort_values("revenue")["pct_revenue"])):
        ax.text(seg.sort_values("revenue")["revenue"].div(1e6).iloc[i], i,
                f"  {c:.0f}% cust / {r:.0f}% rev", va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(FIG / "rfm_revenue.png", dpi=150)
    plt.close()
    champ = seg.loc["Champions"] if "Champions" in seg.index else seg.iloc[0]
    out.append(f"- **Revenue concentrates in a few segments:** *{seg.index[0]}* are "
               f"{seg.iloc[0]['pct_customers']:.0f}% of customers but "
               f"{seg.iloc[0]['pct_revenue']:.0f}% of revenue — the segment to protect.")

    # ── 3. Pareto (revenue concentration) ────────────────────────────────────
    cust_rev = rfm.sort_values("monetary", ascending=False)["monetary"].reset_index(drop=True)
    cum = cust_rev.cumsum() / cust_rev.sum() * 100
    top20_share = cum.iloc[int(len(cum) * 0.2)]
    plt.figure(figsize=(9, 5))
    plt.plot(np.arange(len(cum)) / len(cum) * 100, cum, color="#e76f51")
    plt.axvline(20, color="grey", ls="--")
    plt.axhline(top20_share, color="grey", ls=":")
    plt.xlabel("% of customers (highest-value first)")
    plt.ylabel("% of cumulative revenue")
    plt.title(f"Revenue Pareto — top 20% of customers = {top20_share:.0f}% of revenue")
    plt.tight_layout()
    plt.savefig(FIG / "revenue_pareto.png", dpi=150)
    plt.close()
    out.append(f"- **Pareto:** the top 20% of customers drive **{top20_share:.0f}%** of revenue "
               f"— retention/loyalty spend should be concentrated there.")

    # ── 4. monthly revenue trend ─────────────────────────────────────────────
    monthly = df.groupby("invoice_month")["revenue"].sum() / 1e6
    monthly.index = monthly.index.astype(str)
    monthly.to_csv(OUTD / "monthly_revenue.csv")
    plt.figure(figsize=(11, 5))
    monthly.plot(color="#2a9d8f", marker="o")
    plt.ylabel("Revenue (GBP M)")
    plt.xlabel("Month")
    plt.title("Monthly revenue")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(FIG / "monthly_revenue.png", dpi=150)
    plt.close()

    (OUTD / "growth_summary.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    print(f"\nfigures -> {FIG}")


if __name__ == "__main__":
    main()
