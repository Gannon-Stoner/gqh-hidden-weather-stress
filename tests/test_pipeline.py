"""End-to-end smoke test of run_all.py on synthetic prices and features (no licensed data).

Synthetic numbers exercise the code path only; they are not market evidence.
Run: python tests/test_pipeline.py
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_all  # noqa: E402


def synthetic(tmp: Path, seed=3):
    rng = np.random.default_rng(seed)
    S = pd.bdate_range("2020-07-01", "2026-04-30")
    months = pd.period_range("2020-08", "2027-06", freq="M")
    rows, defs = [], []
    level = 3 + np.cumsum(rng.normal(0, 0.05, len(S)))
    for i, mth in enumerate(months):
        last = (mth.to_timestamp() - pd.offsets.BDay(3)).normalize()
        live = S[S <= last]
        basis = 0.02 * (i % 12) + np.cumsum(rng.normal(0, 0.01, len(live)))
        for d, b in zip(live, basis):
            rows.append((d, 1000 + i, f"NG{mth}", level[S.get_loc(d)] + b, 1))
        defs.append((1000 + i, f"NG{mth}", mth.year, mth.month, last))
    pd.DataFrame(rows, columns=["date", "instrument_id", "symbol", "price", "final"]).to_csv(
        tmp / "ng_settle.csv", index=False)
    pd.DataFrame(defs, columns=["instrument_id", "raw_symbol", "maturity_year", "maturity_month",
                                "last_trade"]).to_csv(tmp / "ng_definitions.csv", index=False)
    init = pd.date_range("2020-10-31", "2026-03-31", freq="D")
    f = pd.DataFrame({"init": init, "winter": 0, "is_dev": True, "is_holdout": False,
                      "n_members": 31, "a": rng.normal(10, 3, len(init))})
    f["a_z"] = (f["a"] - 10) / 3
    f["b1_signal"] = f["a_z"] > 1.28
    f["p_cold"] = np.clip(rng.beta(1, 8, len(init)), 0, 1)
    f["p_warm"] = np.clip(rng.beta(1, 8, len(init)), 0, 1)
    for c in ("K", "dK_star", "B", "d_a", "d_p_cold", "d_B"):
        f[c] = rng.normal(0, 1, len(init))
    f.to_csv(tmp / "features.csv", index=False)


def test_run_all_end_to_end():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        synthetic(tmp)
        run_all.main(True, tmp, tmp / "features.csv", out=tmp / "results")
        s = pd.read_csv(tmp / "results" / "summary.csv")
        assert {"H1", "B0_always_long", "R7_outright"} <= set(s["variant"])
        assert set(s["period"]) == {"dev", "holdout"}
        assert (tmp / "results" / "equity.png").exists()
        r = pd.read_csv(tmp / "results" / "regressions.csv")
        assert {"M1", "M4", "P1"} <= set(r["model"])
        print(s[(s.costs == "1x") & (s.variant.isin(["H1", "B0_always_long"]))].round(3).to_string())


if __name__ == "__main__":
    test_run_all_end_to_end()
    print("pipeline test passed")
