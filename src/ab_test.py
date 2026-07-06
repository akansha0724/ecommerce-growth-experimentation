"""
ab_test.py — Design and analyse an experiment the growth team would actually
run, with the statistics done properly.

Scenario: a win-back email with a discount, sent to the **At-risk** RFM segment,
aiming to lift 30-day reactivation. The dataset has no randomised assignment, so
the experiment is *simulated* — but every step (power analysis, sample sizing,
two-proportion test, and the peeking-trap demonstration) is the real workflow.

Writes reports/ab_test.md + two figures.
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
from prep import load, customer_rfm, ROOT  # noqa: E402

FIG = ROOT / "reports" / "figures"
RNG = np.random.default_rng(42)

# ── experiment design parameters (documented assumptions) ────────────────────
BASELINE = 0.12        # assumed 30-day reactivation rate for At-risk (control)
TRUE_LIFT = 0.05       # true treatment effect used for the simulated run (+5pp)
MDE = 0.04             # minimum detectable effect we power the test for (+4pp)
ALPHA = 0.05
POWER = 0.80


def sample_size(p1, p2, alpha=ALPHA, power=POWER) -> int:
    """Per-arm n for a two-proportion two-sided test (normal approximation)."""
    za = stats.norm.ppf(1 - alpha / 2)
    zb = stats.norm.ppf(power)
    n = (za + zb) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p2 - p1) ** 2
    return int(np.ceil(n))


def two_prop_z(x1, n1, x2, n2):
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / se
    return z, 2 * (1 - stats.norm.cdf(abs(z)))


def main():
    df = load()
    rfm = customer_rfm(df)
    at_risk = int((rfm["segment"] == "At risk").sum())

    out = ["# A/B test — win-back email to the At-risk segment", ""]
    out.append("*Simulated experiment (the dataset has no randomised arms) — but the design, "
               "sizing, and analysis are the real workflow.*")
    out.append("")
    out.append("## Design")
    out.append(f"- **Unit:** customer · **population:** At-risk RFM segment "
               f"(**{at_risk:,}** available in the data)")
    out.append(f"- **Metric:** 30-day reactivation (made a purchase) — a proportion")
    out.append(f"- **H0:** treatment reactivation = control · **H1:** treatment > control")
    out.append(f"- **Assumed control rate:** {BASELINE*100:.0f}% · **MDE:** +{MDE*100:.0f}pp "
               f"· **alpha:** {ALPHA} · **power:** {POWER}")

    # ── power analysis: required sample size ──────────────────────────────────
    n_req = sample_size(BASELINE, BASELINE + MDE)
    out.append("")
    out.append("## Power analysis")
    out.append(f"- **Required sample: {n_req:,} per arm** ({2*n_req:,} total) to detect a "
               f"+{MDE*100:.0f}pp lift at {int(POWER*100)}% power.")
    feasible = "yes" if 2 * n_req <= at_risk else "no — would need a smaller MDE or a multi-send"
    out.append(f"- Feasible within the At-risk pool? **{feasible}** "
               f"(pool {at_risk:,} vs need {2*n_req:,}).")

    mdes = np.linspace(0.02, 0.08, 25)
    ns = [sample_size(BASELINE, BASELINE + m) for m in mdes]
    plt.figure(figsize=(9, 5))
    plt.plot(mdes * 100, ns, color="#2a9d8f")
    plt.axvline(MDE * 100, color="#e76f51", ls="--", label=f"chosen MDE +{MDE*100:.0f}pp")
    plt.xlabel("Minimum detectable effect (pp)")
    plt.ylabel("Required sample size per arm")
    plt.title("Smaller effects cost exponentially more sample")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG / "power_curve.png", dpi=150)
    plt.close()

    # ── one simulated run at the true effect ─────────────────────────────────
    n = n_req
    ctrl = RNG.binomial(n, BASELINE)
    trt = RNG.binomial(n, BASELINE + TRUE_LIFT)
    z, p = two_prop_z(ctrl, n, trt, n)
    lift = trt / n - ctrl / n
    se = np.sqrt((trt/n)*(1-trt/n)/n + (ctrl/n)*(1-ctrl/n)/n)
    ci = (lift - 1.96 * se, lift + 1.96 * se)
    out.append("")
    out.append("## Simulated result (true effect +5pp)")
    out.append(f"- Control {ctrl/n*100:.1f}% vs treatment {trt/n*100:.1f}% — "
               f"observed lift **+{lift*100:.1f}pp** (95% CI {ci[0]*100:.1f} to {ci[1]*100:.1f}pp)")
    out.append(f"- z = {z:.2f}, **p = {p:.4f}** → "
               f"{'reject H0 — ship it' if p < ALPHA else 'inconclusive'}")

    # ── the peeking trap ─────────────────────────────────────────────────────
    # Under the NULL (no real effect), naive significance-checking at every
    # interim look inflates the false-positive rate far above alpha.
    LOOKS, SIMS = 10, 3000
    single_fp = peek_fp = 0
    for _ in range(SIMS):
        c = RNG.binomial(1, BASELINE, n)
        t = RNG.binomial(1, BASELINE, n)   # SAME rate — null is true
        sig_ever = False
        for k in range(1, LOOKS + 1):
            j = n * k // LOOKS
            _, pk = two_prop_z(c[:j].sum(), j, t[:j].sum(), j)
            if pk < ALPHA:
                sig_ever = True
        _, pf = two_prop_z(c.sum(), n, t.sum(), n)
        single_fp += pf < ALPHA
        peek_fp += sig_ever
    single_fp, peek_fp = single_fp / SIMS, peek_fp / SIMS

    plt.figure(figsize=(7, 5))
    plt.bar(["Single look\n(correct)", f"Peeking at {LOOKS} looks\n(the trap)"],
            [single_fp * 100, peek_fp * 100], color=["#2a9d8f", "#e76f51"])
    plt.axhline(ALPHA * 100, color="grey", ls="--", label=f"intended {ALPHA*100:.0f}%")
    plt.ylabel("False-positive rate under the null (%)")
    plt.title("Why you don't peek: repeated checking inflates false positives")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG / "peeking_trap.png", dpi=150)
    plt.close()

    out.append("")
    out.append("## The peeking trap (why experiment discipline matters)")
    out.append(f"- Simulated under the **null** (no real effect): a single look at the end "
               f"falsely 'wins' **{single_fp*100:.1f}%** of the time (as designed, ~5%).")
    out.append(f"- But checking significance at every interim look and stopping on the first "
               f"'win' falsely 'wins' **{peek_fp*100:.1f}%** of the time — "
               f"**{peek_fp/single_fp:.1f}x the intended false-positive rate.**")
    out.append("- **Takeaway:** fix the sample size up front and read the result once; if you "
               "must monitor, use a sequential-testing correction (e.g. alpha-spending).")

    (ROOT / "reports" / "ab_test.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
