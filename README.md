# Hidden weather stress in Henry Hub calendar spreads

Gator Quant Hacks 2026, Systematic Trading track. Solo entry: Gannon Stoner.

**Question.** A national gas-weighted heating-degree-day (HDD) forecast is what most of the
gas market trades on. It throws away three pieces of the same ensemble forecast:

- how many ensemble scenarios show extreme cold (tail probability);
- whether the cold scenarios are also the low-wind scenarios (co-stress dependence);
- whether the cold lands on producing basins (freeze-off exposure).

Does that discarded information predict returns on the NYMEX natural-gas front calendar
spread (NG1 − NG2) after executable fills and costs?

**Pre-registration.** Before any price data was loaded, the hypothesis, signals, trading rule,
holdout and decision criteria were frozen in [`PREREGISTRATION.md`](PREREGISTRATION.md)
(commit `8810216`). Every variant and amendment is logged in [`TRIALS.md`](TRIALS.md).

## Reproduce the headline numbers

```bash
pip install -r requirements.txt
cp .env.example .env               # add DATABENTO_API_KEY
python data/download_prices.py     # prints the exact Databento cost quote, buys nothing
python data/download_prices.py --buy --max-usd 50
python run_all.py --include-holdout
```

`run_all.py` reads the committed weather features (`data/weather_features.csv`) and the
NG settlements, and writes everything into `results/`:

| File | Contents |
|---|---|
| `summary.csv` | Required metrics for development and holdout at 1× and 2× costs, every variant |
| `equity.png` | Equity curves |
| `regressions.csv` | Information ladder |
| `h1_by_winter.csv`, `trades_*.csv` | Per-winter results and contract-level trade ledgers |
| `extra.json` | Bootstrap intervals and leave-one-storm-out results |

Without `--include-holdout`, holdout prices are masked. This is the development mode.

### Rebuilding the weather features (optional, about 85 minutes)

```bash
python data/build_weights.py                          # 2019 EIA weights -> data/region_weights.csv
python data/build_weather_features.py --workers 8     # GEFS chunks -> data/cache/gefs/
python data/build_weather_features.py --combine       # -> data/member_features.npz
python -m src.signals                                 # -> data/weather_features.csv
```

The GEFS archive is read directly from dynamical.org's public Icechunk/Zarr store, with no
account or key. Only the chunks containing the 31 fixed region anchors are read, about 50 MB
per forecast run. With 4 workers on a home connection this measured about 5.5 s per run,
or roughly 85 minutes for all 912 winter runs. The repository includes a `.devcontainer`
for running it in a GitHub Codespace instead.

## Strategy in one paragraph

Every session D at 14:00 ET, use the GEFS 00 UTC run from that morning, which is public by
about 02:00 ET. For each of 31 members, compute population-gas-weighted HDD over gas days
D+6 to D+14. `p_cold` is the share of members above that calendar month's development 90th
percentile. If `p_cold ≥ 0.30`, buy the NG1 − NG2 spread at D's settlement through
Trade-at-Settlement orders, and sell it at the settlement five sessions later. Sizing targets
1% of NAV per five-session standard deviation, with a 3% NAV stop. Costs are one tick plus
$2.50 per leg per side, and every result is also reported at 2× costs. The ensemble-mean rule
(B1) and always-long (B0) are the baselines. Co-stress dependence `K` and basin freeze
exposure `B` are tested as nested increments.

## Repository layout

```
PREREGISTRATION.md     frozen hypothesis, rule, holdout, criteria
TRIALS.md              trial register and dated amendments
run_all.py             one command -> results/
src/config.py          every constant from the pre-registration
src/regions.py         fixed region anchors
src/signals.py         p_cold, mean anomaly, K, basin cold, revisions
src/backtest.py        contract-level settlement ledger (fixed contract ids, costs, stop)
src/analysis.py        metrics, HAC information ladder, block bootstrap, storm drops
data/build_weights.py, data/build_weather_features.py, data/download_prices.py
tests/                 hand-checked ledger test; synthetic end-to-end pipeline test
```

## Data and licences

| Source | Licence | In repo? |
|---|---|---|
| NOAA GEFS v12 via [dynamical.org](https://dynamical.org/catalog/noaa-gefs-forecast-35-day/) | CC BY 4.0 | Derived features only |
| EIA consumption, EIA-860, Drilling Productivity Report | Public domain | Derived weights only |
| Databento GLBX.MDP3 NG settlements and definitions | Licensed | **No**; download with your key |

## Key references

- Monteux, Arcuri, Gandolfi & Caselli (2025), *North American Journal of Economics and
  Finance* 80, 102494. Extreme-cold forecasts and an NG1 − NG2 premium.
- Hsu, Park & Zhu (2026), "Weather Forecasts, Forecast Revisions, and Natural Gas Price
  Discovery", SSRN 7411255.
- Taylor & Buizza (2002), *IEEE Transactions on Power Systems* 17:626–632. Ensemble-based
  nonlinear demand.
- Gu, Kurov & Stan (2026), *Journal of Futures Markets* 46(7). Trader attention and
  fundamental news.
- Bailey & López de Prado (2014), "The Deflated Sharpe Ratio".
