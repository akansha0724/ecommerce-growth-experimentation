# A/B test — win-back email to the At-risk segment

*Simulated experiment (the dataset has no randomised arms) — but the design, sizing, and analysis are the real workflow.*

## Design
- **Unit:** customer · **population:** At-risk RFM segment (**824** available in the data)
- **Metric:** 30-day reactivation (made a purchase) — a proportion
- **H0:** treatment reactivation = control · **H1:** treatment > control
- **Assumed control rate:** 12% · **MDE:** +4pp · **alpha:** 0.05 · **power:** 0.8

## Power analysis
- **Required sample: 1,178 per arm** (2,356 total) to detect a +4pp lift at 80% power.
- Feasible within the At-risk pool? **no — would need a smaller MDE or a multi-send** (pool 824 vs need 2,356).

## Simulated result (true effect +5pp)
- Control 12.2% vs treatment 15.3% — observed lift **+3.1pp** (95% CI 0.3 to 5.8pp)
- z = 2.15, **p = 0.0313** → reject H0 — ship it

## The peeking trap (why experiment discipline matters)
- Simulated under the **null** (no real effect): a single look at the end falsely 'wins' **4.6%** of the time (as designed, ~5%).
- But checking significance at every interim look and stopping on the first 'win' falsely 'wins' **18.8%** of the time — **4.1x the intended false-positive rate.**
- **Takeaway:** fix the sample size up front and read the result once; if you must monitor, use a sequential-testing correction (e.g. alpha-spending).