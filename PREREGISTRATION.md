# Pre-registration: hidden weather stress in Henry Hub calendar spreads

Author: Gannon Stoner (solo). Gator Quant Hacks 2026, Systematic Trading track.
Committed before any natural-gas price data was downloaded or analysed by this project.
Any later change is logged in `TRIALS.md` as a dated amendment; this file is not rewritten.

## 1. Research question

A national gas-weighted heating-degree-day (HDD) forecast is the summary most of the
natural-gas market trades on. It discards three pieces of the same ensemble forecast:

1. **Tail probability** — how many ensemble scenarios show extreme cold, not just the mean.
2. **Co-stress dependence** — whether the cold scenarios are also the low-wind scenarios
   (same marginals, different pairing).
3. **Location** — whether cold falls on producing basins (freeze-off risk) rather than on
   consuming regions.

Does this discarded information predict returns on the NYMEX Henry Hub front calendar
spread (NG1 − NG2) after an executable delay and costs, beyond the ensemble-mean forecast?

## 2. Economic hypothesis (written before results)

- **Mechanism.** Gas scarcity is convex in demand: storage deliverability, freeze-offs and
  power-sector substitution bind only in the cold tail. Tail cold therefore tightens the
  prompt month more than later months (weather-driven backwardation).
- **Prior evidence.** Monteux, Arcuri, Gandolfi & Caselli (2025, NAJEF 80) report a
  non-linear premium in NG1 − NG2 after extreme-cold forecasts (1990–2019, deterministic
  forecasts). Hsu, Park & Zhu (2026, SSRN 7411255) show forecast revisions move NG prices.
- **Our extension.** Replace the deterministic forecast with ensemble tail probability,
  test out of sample (2020–2026) with executable settlement fills, and test whether
  co-stress dependence and basin cold add information.
- **Counterparty.** Hedgers and speculators who trade consensus mean-HDD revisions and
  must pay to carry prompt short exposure into possible scarcity; limited attention to
  distributional information (Gu, Kurov & Stan 2026, J. Futures Markets).
- **Why it could persist.** Member-level multivariate stress requires ensemble archives
  and processing that most public weather products (ensemble-mean HDD) do not provide;
  the premium may also be compensation for genuine tail risk.
- **Falsifiers.** No incremental predictive value of tail probability beyond the mean;
  edge confined to one storm; gross edge removed by 2× costs; effect only before entry.

## 3. Data

| Input | Source | Use |
|---|---|---|
| GEFS v12 operational ensemble, 00 UTC, 31 members, `temperature_2m`, `wind_u_100m`, `wind_v_100m` | dynamical.org `noaa-gefs-forecast-35-day` (CC BY 4.0), inits from 2020-10-01 | Signals |
| NG futures settlements and definitions | Databento GLBX.MDP3 (`statistics`, `definition`) | Returns, contract calendar |
| Gas-demand weights | EIA 2019 residential + commercial gas consumption by state | Fixed, pre-sample |
| Wind weights | EIA-860 2019 wind nameplate capacity by plant location | Fixed, pre-sample |
| Basin weights | EIA 2019 dry-gas production by basin | Fixed, pre-sample |

Weights are computed by committed scripts and frozen before any price data is loaded.
Derived weather features are committed; licensed price data is never committed.

## 4. Clock (no lookahead)

- Decision session D (CME trade date). Signal uses the GEFS 00 UTC run initialised on
  calendar date D, publicly available by about 02:00 ET (≈12 h before the decision).
- Decision 14:00 ET. **Entry**: Trade-at-Settlement (TAS) on both legs at D's settlement
  (14:28–14:30 ET VWAP). **Exit**: TAS at the settlement of session D+5.
- Contracts: NG1 = nearest NG outright whose last trade date is at least 2 sessions after
  the planned exit; NG2 = the next listed month. Contract IDs are fixed for the trade.

## 5. Signals

Regions use 3×3 grid-point neighbourhoods (0.75°) around fixed anchors (`src/regions.py`).
Gas day g = 15 UTC to 15 UTC. All averages are over the 3-hourly/6-hourly steps in g.

- **Gas-weighted HDD**: `H[m,g] = Σ_r w_r · max(18 − T[m,r,g], 0)` (°C·day), demand weights w.
- **Week-2 cold**: `Hbar[m] = mean of H[m,g] over gas days D+6 … D+14`.
- **Tail threshold** `τ(month)`: 90th percentile of `Hbar[m]` over all members of development
  inits in that calendar month, computed leave-one-winter-out inside development; the
  full-development value is frozen for the holdout.
- **Tail probability (primary)**: `p_cold = share of members with Hbar[m] > τ(month)`.
- **Mean signal (baseline)**: `a = ensemble-mean Hbar`, standardised by month on development.
- **Co-stress dependence K** (gas days D+2 … D+5): `x = H[m,g]`; calm `y = 1 − CF[m,g]`, where
  CF is wind-capacity-weighted fleet capacity factor from 100 m wind through a generic power
  curve (cut-in 3, rated 12, cut-out 25 m/s; output derated linearly to zero from −20 °C to
  −30 °C). `K = mean_g cov_m(x, y)`; also report `ρ = mean_g corr_m(x, y)`.
- **Basin cold** (gas days D+2 … D+5): `B = Σ_b u_b · max(0 − T[m,b,g], 0)`, ensemble mean,
  production weights u.

## 6. Primary trading rule (one rule)

When flat at 14:00 ET on D and `p_cold ≥ 0.30` (≥ 3× the unconditional 10% rate):
buy the NG1 − NG2 spread at D's settlement, sell it at D+5's settlement. One position at a
time; re-entry at an exit settlement is allowed and charged full costs. Months Nov–Mar only.

- **Sizing**: NAV $1,000,000. Spreads `q = clip(round(0.01·NAV / σ5), 1, 25)`, where σ5 is
  √5 × EWMA(λ = 0.94) s.d. of daily dollar changes of one front spread over the prior 60
  sessions. **Stop**: exit at the next settlement if open loss exceeds 3% of NAV.
- **Costs** per leg per side: 1 tick ($10) + $2.50 fees → $50 per spread round trip.
  All results also at 2× costs.

## 7. Comparisons and tests (all reported, none selected)

- **Ladder of rules (same clock, sizing, costs):** B0 always long spread Nov–Mar;
  B1 ensemble-mean rule (`a` above its development 90th percentile); H1 primary.
- **Nested forward regressions** (vol-normalised 5-session spread return, Newey-West lags 5):
  M1 `a`; M2 `+ p_cold`; M3 `+ K`; M4 `+ B`. Innovation claims require the increment.
- **"Is it priced?"**: same-day return (D−1 → D settlement) on daily changes of each signal.
- **Robustness (disclosed, not selectable):** entry one session later; holds 3 and 10;
  thresholds 0.20 and 0.40; symmetric warm-tail short side; NG1 outright instead of spread.
- **Concentration:** results by winter, leave-one-episode-out (Feb 2021, Dec 2022,
  Jan 2024, Jan 2025), longs only by construction, block bootstrap by week.
- **Required metrics:** annualised return, volatility, Sharpe, max drawdown, turnover,
  worst month, equity curve, separately for development and holdout, at 1× and 2× costs.

## 8. Development and holdout

Common-source history: 2020-10-01 to 2026-10-03 (6.0 years). Holdout = most recent
min(20%, 2 years) = 1.2 years (438.6 days) → sessions on or after **2025-07-22**, i.e. winter 2025–26.
Development: winters 2020–21 to 2024–25. The holdout is evaluated once, at a tagged commit,
after code and development report are frozen.

## 9. Decision criteria

- H1 is supported in development only if net Sharpe > 0 at 2× costs **and** the `p_cold`
  increment in M2 has Newey-West t > 2. Holdout results are reported whatever they show.
- K or basin cold is claimed as incremental only if t > 2 in development **and** the
  holdout coefficient has the same sign.
- A noisy null is reported as inconclusive with its confidence interval, not as no edge.
- No sign flips, new filters or threshold changes after the holdout is viewed.

## 10. Prior-knowledge disclosure

No NG price series for 2020–2026 has been analysed by this project. The author knows of
major storms (Uri 2021, Elliott 2022, January 2024/2025 cold, Fern 2026) and has read a
public report of the February–March 2026 spread spike during Fern (holdout period).
The research families in the author's earlier Loxias evidence ledger (equity month-end,
ES/ZN, third-Friday, VIX ETP, WASDE corn, ETF trend, HMM) did not study NG weather signals.
No Loxias code is used in this repository.
