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

## Correctness amendment — 2026-10-03 (Codex; recorded before corrected development returns)

This amendment is recorded before calculating corrected development returns. Original
pre-registration and original development results remain historical records. No holdout
returns are evaluated. Prior exposure to the Fern prices remains disclosed above.

Outcome-independent primary fixes:
- Parse both residential and commercial EIA header formats; require all 49 covered states/DC
  and rebuild registered residential + commercial weights. Retain original weight vintage.
- Remove copied Good Friday marks from the NG trading-session index (CME 2021/2023 notices).
- Match same-day diagnostic revisions to the previous market session, with plain changes
  in K. Preserve the calendar-day/dK-star calculation as P1_legacy_calendar. Also report
  the actual eligible pair and Monday/Tue–Fri comparisons; these are diagnostics.
- Subtract each excluded trade's own daily P&L, including fees, instead of zeroing dates
  shared with other trades. Use the registered calendar-month episode windows.
- Refuse missing settlement marks during an open position and incomplete end-of-data holds.
  Include the initial NAV in drawdowns. Use the registered sqrt(5) risk horizon for hold
  variants R2/R3; retain their original results in the as-run archive.
- Filter holdout prices before aggregation, build development features by default, preserve
  b_hat metadata, report observed coverage and winter-session metrics, and export both
  cost equity curves. Public trade ledgers omit settlement values.

Primary H1 still uses the registered monthly LOWO thresholds, level trigger, delivery-pair
selection, five-session hold and original front-spread EWMA sizing. The actual code used
60 observations as an expanding-EWMA warm-up, not a finite 60-session window. Since these
choices are documented in the pre-registration/as-run design and some holdout information
was seen, their alternatives are not silently substituted or chosen by development returns.

One explicitly post-hoc development-only risk comparison is added: H1_matched_pair_risk
uses the actual eligible contract pair's strictly prior 60 daily changes, exponentially
weighted at lambda=.94. The 1% target, cap, stop, entry and exit rules are identical.
This repairs the sizing interpretation in a separately identified version; it does not
replace H1 or create an independent out-of-sample claim.

One fixed development-only timing diagnostic is added: for first session crossings of
p_cold >= .30, report fixed-pair normalized paths from five sessions before to five after
entry, with individual event rows. Also report level/one-session-return lead-lags, using
HAC(5). These are exploratory associations, not causal proof or new trading rules. All
lags -5 through +5 are reported, with no selected best lag and no holdout evaluation.

Disclosure corrections: there were five original regression specifications and 14 reported
coefficient tests, not five independent tests. The original corr(K,a_z)=.05 included holdout
weather. Recomputed statistics in this amendment use development dates only. Forecast
initialization is not publication time; the cache does not prove historical per-run
availability. The 14:00 decision / settlement fill remains an execution assumption.

### Corrected development results — 2026-10-04T00:30:55.928643+00:00

H1: 22 trades, $20,430 net at 1x costs (Sharpe 0.105169); $8,080 at 2x
(Sharpe 0.041448). M2 p_cold t=-0.749188; registered development support fails.
H1_matched_pair_risk: $27,870 at 1x (Sharpe 0.113943), $8,520 at 2x
(Sharpe 0.034667), with larger drawdown (-7.574% vs -6.080%). No sizing winner selected.
20 repair regression tests, two original ledger tests and the synthetic pipeline passed.
All 761 development per-run weather caches matched the combined array exactly.
No real holdout returns or corrected holdout signals evaluated; no new data purchases.
See docs/REPAIR_REPORT_2026-10-03.txt for limitations, sources and the timing diagnostics.

## Amendment A1 — declared 2026-10-03 before any rerun (post-audit, holdout still unevaluated)

An independent audit (`docs/AUDIT_2026-10-03.md`) found code deviations from this pre-registration. Each fix below restores the registered text or corrects a reporting bug; none is chosen by outcome. Decision rule fixed now: the **registered (corrected) specification is primary**; the as-run development numbers above stay in this log.

| Fix | Registered text | Was | Now |
|---|---|---|---|
| A1.1 | §3 demand weights = residential + commercial | commercial file parsed 0 states | parse both; assert ≥ 48 states each |
| A1.2 | §8 history to 2026-10-03 | prices ended 2026-04-30 | prices extended to 2026-10-02; holdout = 2025-07-22 … 2026-10-02 |
| A1.3 | §7 episodes = Feb 2021, Dec 2022, Jan 2024, Jan 2025 (calendar months) | custom windows; drop also zeroed a neighbouring trade's day | calendar months; subtract each dropped trade's own P&L |
| A1.4 | §6/§7 σ5 = √5·σ for every variant | R2/R3 used √hold | √5 for all |
| A1.5 | §7 B1 = `a` above its development 90th percentile | per-month leave-one-winter-out | single pooled development percentile |
| A1.6 | §7 P1 = same-day return on daily changes of each signal | calendar-day changes, b̂-adjusted K | changes vs the previous session's init for a, p_cold, K, B; traded-pair and nearest-pair versions; Monday vs Tue–Fri split; as-run P1 kept |
| A1.7 | §5 also report ρ; §7 equity curve at 1× and 2×; §7 block bootstrap by week | missing / moving 5-session blocks | ρ reported; 2× curves; calendar-week blocks |
| A1.8 | — | Good Friday rows repeating prior settlement treated as sessions | drop rows identical to the previous session |
| A1.9 | — | winter and full-period metrics mixed with idle summers | add winter-session (Nov–Apr) metrics for dev and holdout alongside the registered all-session metrics |

Wording corrections (no number changes): §3 basin weights are EIA DPR "natural gas total production", not dry gas; §4 00Z availability measured ≈ 01:30 EST / 02:30 EDT; §6 EWMA(0.94) needs 60 prior sessions but has an ≈ 11-session half-life; TRIALS 16:30 corr(K, a_z) dev-only is 0.106; regression count is 14 coefficient tests, not 5 specs.

Not changed (disclosed as limitations, because holdout outcomes for Fern are already known): init-month thresholds, contract-pair selection and buffer, level rule, sizing σ source.

Post-hoc diagnostic (labelled, not a trading rule): pre-entry event study and lead-lag of `a_z` on spread returns.
