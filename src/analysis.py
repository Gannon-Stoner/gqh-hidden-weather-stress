"""Performance metrics, nested information regressions, bootstrap and concentration checks."""
import numpy as np
import pandas as pd
import statsmodels.api as sm

from src import config as C

DEV = ("2020-11-01", pd.Timestamp(C.HOLDOUT_START) - pd.Timedelta(days=1))
HOLD = (C.HOLDOUT_START, "2026-04-30")
EPISODES = {"Uri 2021-02": ("2021-02-01", "2021-02-28"),
            "Elliott 2022-12": ("2022-12-15", "2023-01-05"),
            "Jan 2024": ("2024-01-05", "2024-01-25"),
            "Jan 2025": ("2025-01-10", "2025-01-31")}


def metrics(pnl, notional, trades, period):
    p = pnl.loc[period[0]:period[1]]
    if p.empty:
        return {}
    r = p / C.NAV
    years = len(r) / 252
    cum = r.cumsum()
    tr = trades[(trades["entry"] >= pd.Timestamp(period[0])) &
                (trades["entry"] <= pd.Timestamp(period[1]))] if len(trades) else trades
    sd = r.std(ddof=1)
    return {
        "ann_return": r.mean() * 252,
        "ann_vol": sd * np.sqrt(252),
        "sharpe": r.mean() / sd * np.sqrt(252) if sd > 0 else np.nan,
        "max_drawdown": (cum - cum.cummax()).min(),
        "turnover_x": notional.loc[period[0]:period[1]].sum() / C.NAV / years,
        "worst_month": r.groupby(r.index.to_period("M")).sum().min(),
        "skew": r[r != 0].skew(),
        "n_trades": len(tr),
        "hit_rate": (tr["net"] > 0).mean() if len(tr) else np.nan,
        "total_pnl_usd": p.sum(),
    }


def block_bootstrap_sharpe(pnl, period, block=5, n=2000, seed=7):
    r = (pnl.loc[period[0]:period[1]] / C.NAV).values
    if len(r) < 2 * block or r.std() == 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(len(r) / block))
    out = []
    for _ in range(n):
        idx = (rng.integers(0, len(r) - block + 1, nb)[:, None] + np.arange(block)).ravel()[: len(r)]
        x = r[idx]
        out.append(x.mean() / x.std(ddof=1) * np.sqrt(252) if x.std() > 0 else 0.0)
    return tuple(np.percentile(out, [5, 95]))


def drop_episodes(pnl, trades):
    """Sharpe-relevant P&L with each named episode's trades removed in turn."""
    out = {}
    for name, (a, b) in EPISODES.items():
        q = pnl.copy()
        hit = trades[(trades["entry"] >= a) & (trades["entry"] <= b)] if len(trades) else trades
        for _, t in hit.iterrows():
            q.loc[t["entry"]:t["exit"]] = 0.0
        out[name] = q
    return out


def forward_returns(mkt, sigma, hold=C.HOLD_SESSIONS):
    """Vol-normalised spread return from settlement t to t+hold, ids fixed at t."""
    S = mkt.sessions
    y = np.full(len(S), np.nan)
    for t in range(len(S) - hold):
        pr = mkt.pair(t, hold)
        if pr and np.isfinite(sigma.iloc[t]) and sigma.iloc[t] > 0:
            dv = mkt.value(pr, [1, -1], t + hold) - mkt.value(pr, [1, -1], t)
            y[t] = dv * C.MULTIPLIER / (sigma.iloc[t] * np.sqrt(hold))
    return pd.Series(y, index=S)


def same_day_returns(mkt, sigma):
    """Vol-normalised spread return from settlement t-1 to t (ids fixed at t-1)."""
    S = mkt.sessions
    y = np.full(len(S), np.nan)
    for t in range(1, len(S)):
        pr = mkt.pair(t - 1, 0)
        if pr and np.isfinite(sigma.iloc[t]) and sigma.iloc[t] > 0:
            y[t] = (mkt.value(pr, [1, -1], t) - mkt.value(pr, [1, -1], t - 1)) * C.MULTIPLIER / sigma.iloc[t]
    return pd.Series(y, index=S)


def hac_ladder(y, X, specs, lags):
    """Nested OLS with Newey-West errors. specs = {name: [columns]}; returns tidy table."""
    rows = []
    for name, cols in specs.items():
        d = pd.concat([y.rename("y"), X[cols]], axis=1).dropna()
        if len(d) < 30:
            continue
        Z = (d[cols] - d[cols].mean()) / d[cols].std(ddof=0)
        fit = sm.OLS(d["y"], sm.add_constant(Z)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
        for c in cols:
            rows.append({"model": name, "term": c, "coef": fit.params[c], "t": fit.tvalues[c],
                         "n": int(fit.nobs), "r2": fit.rsquared})
    return pd.DataFrame(rows)


def by_winter(pnl):
    r = pnl / C.NAV
    w = np.where(r.index.month >= 7, r.index.year, r.index.year - 1)
    g = r.groupby(w)
    return pd.DataFrame({"return": g.sum(), "sharpe": g.mean() / g.std(ddof=1) * np.sqrt(252)})
