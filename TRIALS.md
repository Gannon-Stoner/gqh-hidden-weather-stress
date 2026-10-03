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
| 2026-10-03 15:10 | (this) | Region weights built from 2019 EIA files (demand, EIA-860 wind, DPR basins); no price data loaded. |
