"""Download NYMEX NG futures settlements and contract definitions from Databento.

Needs DATABENTO_API_KEY in .env. Prints the exact cost quote before buying anything and
refuses to spend more than --max-usd. Raw licensed files stay in data/raw/ (gitignored).

    python data/download_prices.py            # quote only
    python data/download_prices.py --buy      # download if quote <= --max-usd
"""
import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import RAW  # noqa: E402

DATASET = "GLBX.MDP3"
SYMBOLS = ["NG.FUT"]
START, END = "2020-07-01", "2026-04-30"   # 4 months of sizing warm-up
OUT = RAW / "databento"
SETTLEMENT_PRICE = 3


def client():
    from dotenv import load_dotenv
    import databento as db
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        sys.exit("DATABENTO_API_KEY missing: copy .env.example to .env and add your key.")
    return db.Historical(key)


def request(c, schema, buy, max_usd):
    kw = dict(dataset=DATASET, symbols=SYMBOLS, stype_in="parent", schema=schema,
              start=START, end=END)
    cost = c.metadata.get_cost(**kw)
    size = c.metadata.get_billable_size(**kw)
    print(f"{schema:12s} quote ${cost:,.2f}  billable {size / 1e6:,.1f} MB")
    path = OUT / f"ng_{schema}.dbn.zst"
    if buy and not path.exists():
        if cost > max_usd:
            sys.exit(f"Quote ${cost:.2f} exceeds --max-usd {max_usd}; not downloading.")
        OUT.mkdir(parents=True, exist_ok=True)
        c.timeseries.get_range(**kw, path=str(path))
        print(f"saved {path}")
    return cost


def settlements_table():
    """Final-preferred daily settlement per outright contract -> data/raw/databento/ng_settle.csv"""
    import databento as db
    st = db.DBNStore.from_file(OUT / "ng_statistics.dbn.zst").to_df(map_symbols=True)
    st = st[st["stat_type"].astype(int) == SETTLEMENT_PRICE].copy()
    # Trade date: ts_ref (session date) when present, else the event's Chicago date.
    ref = pd.to_datetime(st["ts_ref"], utc=True, errors="coerce")
    evt = pd.to_datetime(st["ts_event"], utc=True).dt.tz_convert("America/Chicago")
    ref_date = ref.dt.tz_localize(None).dt.normalize()
    evt_date = evt.dt.tz_localize(None).dt.normalize()
    st["date"] = ref_date.where(ref.notna(), evt_date)
    st["final"] = (st["stat_flags"].astype(int) & 1).astype(int)
    st = st.reset_index().sort_values(["instrument_id", "date", "final", "ts_recv"])
    last = st.groupby(["instrument_id", "date"]).tail(1)
    out = last[["date", "instrument_id", "symbol", "price", "final"]]
    out.to_csv(OUT / "ng_settle.csv", index=False)
    print(f"settlements: {len(out):,} rows, {out['instrument_id'].nunique()} instruments")


def definitions_table():
    """One row per outright NG future: id, symbol, maturity, last trade date."""
    import databento as db
    d = db.DBNStore.from_file(OUT / "ng_definition.dbn.zst").to_df()
    cls = d["instrument_class"].astype(str)
    is_future = cls.isin(["F", "FUTURE", "InstrumentClass.FUTURE"])
    d = d[is_future & (~d["raw_symbol"].str.contains("[- :]"))]
    d = d.sort_values("ts_recv").groupby("instrument_id").tail(1)
    d["last_trade"] = pd.to_datetime(d["expiration"], utc=True).dt.tz_convert("America/Chicago").dt.normalize().dt.tz_localize(None)
    out = d[["instrument_id", "raw_symbol", "maturity_year", "maturity_month", "last_trade"]]
    out = out.sort_values("last_trade")
    out.to_csv(OUT / "ng_definitions.csv", index=False)
    print(f"definitions: {len(out)} outright contracts")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--buy", action="store_true")
    ap.add_argument("--max-usd", type=float, default=50.0)
    a = ap.parse_args()
    c = client()
    total = sum(request(c, s, a.buy, a.max_usd) for s in ("definition", "statistics"))
    print(f"total quote ${total:,.2f}")
    if a.buy:
        definitions_table()
        settlements_table()
