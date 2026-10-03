# Trial register and amendments

Every variant run, every amendment to `PREREGISTRATION.md`, and every data exclusion is
logged here with its date and commit, including failures. Counts feed the note's
"variants tested" disclosure.

## Pre-declared runs (from PREREGISTRATION.md §6–7)

| ID | Rule / test | Role |
|---|---|---|
| H1 | p_cold ≥ 0.30 → long NG1−NG2, TAS D settle → D+5 settle | Primary |
| B0 | Always long NG1−NG2, Nov–Mar | Baseline |
| B1 | Ensemble-mean week-2 HDD above dev 90th pct → long NG1−NG2 | Baseline |
| M1–M4 | Nested forward regressions: a, +p_cold, +K, +B | Information tests |
| P1 | Same-day return on signal changes ("is it priced?") | Diagnostic |
| R1 | H1 with entry one session later | Robustness |
| R2, R3 | H1 holding 3 and 10 sessions | Robustness |
| R4, R5 | H1 thresholds 0.20 and 0.40 | Robustness |
| R6 | Symmetric warm-tail short side | Robustness |
| R7 | NG1 outright instead of spread | Robustness |

Total pre-declared strategy variants: 10 rules (H1, B0, B1, R1–R7) + 5 regression/diagnostic specs.

## Log

| Date (ET) | Commit | Entry |
|---|---|---|
| 2026-10-03 14:49 | 8810216 | Pre-registration committed before any price data. |
| 2026-10-03 14:54 | 867dd63 | Region weights built from 2019 EIA files (demand, EIA-860 wind, DPR basins); no price data loaded. |
| 2026-10-03 15:25 | (next) | Price download (implementation, not a rule change): Databento continuous `NG.c.0`–`NG.c.5` statistics + definitions, 2020-07-01 to 2026-04-30 (4-month sizing warm-up). Quote $0.16. Full `NG.FUT` parent ($12.46, 9.4 GB, mostly spreads) and raw outright symbols (several did not resolve) were tried as quotes/requests and dropped. No returns computed yet. |
| 2026-10-03 16:30 | (next) | Weather features frozen before any return was computed: 913 inits, 31/31 members everywhere, b̂ = 0.341. Pre-price checks only: H1 trigger rate 13.4% dev / 6.6% holdout; corr(p_cold, a_z) = 0.76, corr(K, a_z) = 0.05. |
| 2026-10-03 17:02 | (next) | Price-data validation viewed settlement rows for 2021-02-17, 2022-12-21 and 2026-01-28 (holdout; publicly reported Fern values, already disclosed in §10): NGG26 7.460, NGH26 3.732. No returns or signal-conditional statistics computed on holdout. |
| 2026-10-03 17:03 | (next) | First development run: `python run_all.py` (holdout prices masked). |
| 2026-10-03 17:05 | (this) | Development results (1× costs): H1 Sharpe 0.07 (2× 0.01), 23 trades, 90% block-bootstrap CI [−0.46, 0.68]; B0 0.15; B1 0.14; R1–R7 between −0.35 and 0.20. Forward ladder: p_cold t = −0.70, K t = −0.54, B t = −0.44 (none incremental). Same-day: Δa t = 1.62, ΔB t = 1.76. H1 not supported in development under §9. No rule changed. |
