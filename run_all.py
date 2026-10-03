"""Reproduce every headline number and figure in the quant note.

    python run_all.py                    # development period only (holdout prices masked)
    python run_all.py --include-holdout  # final, run once at the tagged holdout commit

Needs data/weather_features.csv (committed) and NG settlements from
data/download_prices.py (Databento key; raw data is never committed).
"""
import argparse
import json

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src import analysis as A  # noqa: E402
from src import config as C  # noqa: E402
from src.backtest import Market, Spec, ewma_sigma, run  # noqa: E402
from src.signals import load_features  # noqa: E402

DB = C.RAW / "databento"


def load_market(include_holdout, db=DB):
    s = pd.read_csv(db / "ng_settle.csv", parse_dates=["date"])
    wide = s.pivot_table(index="date", columns="instrument_id", values="price", aggfunc="last")
    if not include_holdout:
        wide = wide.loc[: pd.Timestamp(C.HOLDOUT_START) - pd.Timedelta(days=1)]
    defs = pd.read_csv(db / "ng_definitions.csv", parse_dates=["last_trade"])
    return Market(wide, defs)


def make_specs(f, sessions):
    p, pw = f["p_cold"], f["p_warm"]
    h1 = (p >= C.P_COLD_ENTRY).astype(float)
    return [
        Spec("H1", h1),
        Spec("B0_always_long", pd.Series(1.0, index=sessions)),
        Spec("B1_mean_rule", f["b1_signal"].astype(float)),
        Spec("R1_delay1", h1, delay=1),
        Spec("R2_hold3", h1, hold=3),
        Spec("R3_hold10", h1, hold=10),
        Spec("R4_p020", (p >= 0.20).astype(float)),
        Spec("R5_p040", (p >= 0.40).astype(float)),
        Spec("R6_symmetric", h1 - (pw >= C.P_COLD_ENTRY).astype(float)),
        Spec("R7_outright", h1, instrument="outright"),
    ]


def main(include_holdout, db=DB, features=None, out=C.RESULTS):
    out.mkdir(exist_ok=True)
    f = load_features(features) if features else load_features()
    mkt = load_market(include_holdout, db)
    sig = {"spread": ewma_sigma(mkt.front_changes("spread")),
           "outright": ewma_sigma(mkt.front_changes("outright"))}
    periods = {"dev": A.DEV} | ({"holdout": A.HOLD} if include_holdout else {})

    rows, curves, ledgers = [], {}, {}
    for spec in make_specs(f, mkt.sessions):
        for cm in (1.0, 2.0):
            spec.cost_mult = cm
            pnl, notional, trades = run(mkt, spec, sig[spec.instrument])
            for per, rng in periods.items():
                rows.append({"variant": spec.name, "costs": f"{cm:g}x", "period": per,
                             **A.metrics(pnl, notional, trades, rng)})
            if cm == 1.0:
                curves[spec.name], ledgers[spec.name] = pnl, trades
    summary = pd.DataFrame(rows)
    summary.to_csv(out / "summary.csv", index=False, float_format="%.4f")

    h1, h1_tr = curves["H1"], ledgers["H1"]
    extra = {"bootstrap_sharpe_90ci": {p: A.block_bootstrap_sharpe(h1, r) for p, r in periods.items()},
             "dev_sharpe_drop_episode": {k: A.metrics(v, v * 0, h1_tr, A.DEV).get("sharpe")
                                         for k, v in A.drop_episodes(h1, h1_tr).items()},
             "b_hat": None}
    A.by_winter(h1).to_csv(out / "h1_by_winter.csv", float_format="%.4f")
    for name in ("H1", "B0_always_long", "B1_mean_rule"):
        ledgers[name].to_csv(out / f"trades_{name}.csv", index=False)

    # Information ladder (forward) and "is it priced?" (same day), winter sessions
    X = f.reindex(mkt.sessions)
    winter = X.index.month.isin(C.WINTER_MONTHS)
    yf = A.forward_returns(mkt, sig["spread"])
    y0 = A.same_day_returns(mkt, sig["spread"])
    ladder = {"M1": ["a_z"], "M2": ["a_z", "p_cold"], "M3": ["a_z", "p_cold", "K"],
              "M4": ["a_z", "p_cold", "K", "B"]}
    regs = []
    for per, (a, b) in periods.items():
        m = winter & (X.index >= pd.Timestamp(a)) & (X.index <= pd.Timestamp(b))
        fwd = A.hac_ladder(yf[m], X[m], ladder, lags=C.HOLD_SESSIONS)
        now = A.hac_ladder(y0[m], X[m], {"P1": ["d_a", "d_p_cold", "dK_star", "d_B"]}, lags=2)
        regs.append(pd.concat([fwd, now]).assign(period=per))
    pd.concat(regs).to_csv(out / "regressions.csv", index=False, float_format="%.4f")
    (out / "extra.json").write_text(json.dumps(extra, indent=2, default=float))

    fig, ax = plt.subplots(figsize=(8, 4))
    for name in ("H1", "B0_always_long", "B1_mean_rule"):
        ax.plot((curves[name] / C.NAV).cumsum() * 100, label=name)
    if include_holdout:
        ax.axvline(pd.Timestamp(C.HOLDOUT_START), color="grey", ls="--", lw=1)
    ax.set_ylabel("Cumulative net P&L, % of $1M NAV")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "equity.png", dpi=150)
    print(summary[summary["costs"] == "1x"].round(3).to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-holdout", action="store_true")
    ap.add_argument("--prices-dir", default=str(DB), help="folder with ng_settle.csv, ng_definitions.csv")
    ap.add_argument("--features", default=None, help="override features CSV (tests)")
    a = ap.parse_args()
    from pathlib import Path
    main(a.include_holdout, Path(a.prices_dir), a.features)
