"""Contract-level ledger backtest for NG calendar spreads / outrights at settlement (TAS).

Prices are a wide table: index = session date, columns = instrument_id, values = settlement
($/MMBtu). `defs` has instrument_id, last_trade (date). Rules follow PREREGISTRATION.md §4, §6.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src import config as C


@dataclass
class Spec:
    name: str
    signal: pd.Series              # +1 long, -1 short, 0 flat; indexed by decision date
    hold: int = C.HOLD_SESSIONS
    delay: int = 0                 # entry this many sessions after the decision session
    instrument: str = "spread"     # "spread" (NG1 - NG2) or "outright" (NG1)
    cost_mult: float = 1.0


class Market:
    def __init__(self, settle: pd.DataFrame, defs: pd.DataFrame):
        self.px = settle.sort_index()
        self.sessions = self.px.index
        d = defs.dropna(subset=["last_trade"]).sort_values("last_trade")
        d = d[d["instrument_id"].isin(self.px.columns)]
        self.ids = d["instrument_id"].values
        self.last_pos = np.searchsorted(self.sessions, pd.DatetimeIndex(d["last_trade"]).values)

    def pair(self, pos, hold):
        """NG1 = first contract whose last trade is >= hold + buffer sessions after pos."""
        k = np.searchsorted(self.last_pos, pos + hold + C.EXPIRY_BUFFER_SESSIONS)
        if k + 1 >= len(self.ids):
            return None
        return self.ids[k], self.ids[k + 1]

    def value(self, ids, w, pos):
        p = self.px.iloc[pos][list(ids)].values.astype(float)
        return float(np.dot(p, w)) if np.all(np.isfinite(p)) else np.nan

    def front_changes(self, instrument="spread"):
        """Daily $ change of one front spread (or NG1 outright), fixed ids each day; for sizing."""
        w = [1.0, -1.0] if instrument == "spread" else [1.0]
        out = np.full(len(self.sessions), np.nan)
        for t in range(1, len(self.sessions)):
            pr = self.pair(t - 1, 0)
            if pr:
                ids = pr[: len(w)]
                out[t] = (self.value(ids, w, t) - self.value(ids, w, t - 1)) * C.MULTIPLIER
        return pd.Series(out, index=self.sessions)


def ewma_sigma(changes: pd.Series):
    """sigma at t uses changes strictly before t (no lookahead)."""
    x = changes.shift(1)
    var = (x ** 2).ewm(alpha=1 - C.EWMA_LAMBDA, min_periods=C.VOL_LOOKBACK).mean()
    return np.sqrt(var)


def run(mkt: Market, spec: Spec, sigma: pd.Series, entry_months=C.WINTER_MONTHS):
    w = np.array([1.0, -1.0]) if spec.instrument == "spread" else np.array([1.0])
    side_cost = len(w) * (C.SLIP_TICKS_PER_LEG_SIDE * C.TICK * C.MULTIPLIER
                          + C.FEE_PER_LEG_SIDE) * spec.cost_mult
    S = mkt.sessions
    sig = spec.signal.reindex(S).fillna(0.0)
    pnl = pd.Series(0.0, index=S)
    notional = pd.Series(0.0, index=S)
    trades = []
    t = 0
    while t < len(S):
        d = S[t]
        e = t + spec.delay
        if sig.iloc[t] == 0 or d.month not in entry_months or e >= len(S):
            t += 1
            continue
        pr = mkt.pair(e, spec.hold)
        if pr is None:
            t += 1
            continue
        ids = pr[: len(w)]
        s5 = sigma.iloc[e] * np.sqrt(spec.hold)   # sigma must match spec.instrument
        if not np.isfinite(s5) or s5 <= 0:
            t += 1
            continue
        q = int(np.clip(round(C.RISK_FRACTION * C.NAV / s5), 1, C.MAX_SPREADS))
        direction = float(np.sign(sig.iloc[t]))
        v_prev = mkt.value(ids, w, e)
        if not np.isfinite(v_prev):
            t += 1
            continue
        entry_v, open_pnl, x, stopped = v_prev, 0.0, e, False
        pnl.iloc[e] -= q * side_cost
        notional.iloc[e] += q * C.MULTIPLIER * np.abs(mkt.px.iloc[e][list(ids)].values).sum()
        planned = min(e + spec.hold, len(S) - 1)
        while x < planned:
            x += 1
            v = mkt.value(ids, w, x)
            if not np.isfinite(v):
                continue
            step = direction * q * C.MULTIPLIER * (v - v_prev)
            pnl.iloc[x] += step
            open_pnl += step
            v_prev = v
            if open_pnl < -C.STOP_FRACTION * C.NAV and x < planned:
                planned, stopped = min(x + 1, len(S) - 1), True
        pnl.iloc[x] -= q * side_cost
        notional.iloc[x] += q * C.MULTIPLIER * np.abs(mkt.px.iloc[x][list(ids)].values).sum()
        trades.append(dict(decision=d, entry=S[e], exit=S[x], ids=tuple(int(i) for i in ids),
                           direction=direction, q=q, entry_value=entry_v, exit_value=v_prev,
                           gross=open_pnl, costs=2 * q * side_cost, net=open_pnl - 2 * q * side_cost,
                           stopped=stopped))
        t = x  # re-entry allowed at the exit settlement (decision at that session)
        if S[x] == d:
            t += 1
    return pnl, notional, pd.DataFrame(trades)
