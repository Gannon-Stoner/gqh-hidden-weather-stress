"""Hand-checkable ledger tests on synthetic contracts. Run: python tests/test_backtest.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C  # noqa: E402
from src.backtest import Market, Spec, run  # noqa: E402


def market():
    S = pd.bdate_range("2021-01-04", periods=40)
    px = pd.DataFrame({
        1: np.r_[np.linspace(3.0, 3.0, 9), [np.nan] * 31],     # expires early (session 8)
        2: 3.0 + 0.01 * np.arange(40),                           # NG1 during the test
        3: 2.9 + 0.005 * np.arange(40),                          # NG2
        4: np.full(40, 2.8),
    }, index=S)
    defs = pd.DataFrame({"instrument_id": [1, 2, 3, 4],
                         "last_trade": [S[8], S[30], S[39], S[39] + pd.Timedelta(days=30)]})
    return Market(px, defs), S


def test_single_spread_trade():
    m, S = market()
    sigma = pd.Series(10_000.0 / np.sqrt(C.HOLD_SESSIONS) * 1.0, index=S)  # -> q = 1
    sig = pd.Series(0.0, index=S)
    sig.iloc[5] = 1.0
    pnl, notional, tr = run(m, Spec("t", sig), sigma, entry_months=(1, 2))
    assert len(tr) == 1, tr
    t = tr.iloc[0]
    # session 5 + hold 5 + buffer 2 = 12 > last trade of id 1 (8) -> pair (2, 3)
    assert t["ids"] == (2, 3) and t["q"] == 1
    gross = (0.01 - 0.005) * 5 * C.MULTIPLIER                # spread widens 0.005/day for 5 days
    cost = 2 * 2 * (C.TICK * C.MULTIPLIER + C.FEE_PER_LEG_SIDE)
    assert abs(t["gross"] - gross) < 1e-6 and abs(t["net"] - (gross - cost)) < 1e-6
    assert abs(pnl.sum() - (gross - cost)) < 1e-6
    assert t["entry"] == S[5] and t["exit"] == S[10]


def test_delay_and_no_lookahead_in_signal_alignment():
    m, S = market()
    sigma = pd.Series(10_000.0 / np.sqrt(C.HOLD_SESSIONS), index=S)
    sig = pd.Series(0.0, index=S)
    sig.iloc[5] = 1.0
    _, _, tr = run(m, Spec("d", sig, delay=1), sigma, entry_months=(1, 2))
    assert tr.iloc[0]["entry"] == S[6] and tr.iloc[0]["exit"] == S[11]


if __name__ == "__main__":
    test_single_spread_trade()
    test_delay_and_no_lookahead_in_signal_alignment()
    print("backtest tests passed")
