"""Build fixed, pre-sample (2019) region weights from public EIA files.

Writes data/region_weights.csv (committed). Run: python data/build_weights.py
"""
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import RAW, WEIGHTS_CSV  # noqa: E402
from src.regions import BASIN, DEMAND, WIND  # noqa: E402

EIA = RAW / "eia"
URLS = {
    "res": "https://www.eia.gov/dnav/ng/xls/NG_CONS_SUM_A_EPG0_VRS_MMCF_A.xls",
    "com": "https://www.eia.gov/dnav/ng/xls/NG_CONS_SUM_A_EPG0_VCS_MMCF_A.xls",
    "dpr": "https://www.eia.gov/petroleum/drilling/xls/dpr-data.xlsx",
    "860": "https://www.eia.gov/electricity/data/eia860/archive/xls/eia8602019.zip",
}
STATES = {
    "Alabama": "AL", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL",
    "Georgia": "GA", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN",
    "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


def fetch(key):
    EIA.mkdir(parents=True, exist_ok=True)
    path = EIA / URLS[key].rsplit("/", 1)[1]
    if not path.exists():
        req = urllib.request.Request(URLS[key], headers={"User-Agent": "Mozilla/5.0"})
        path.write_bytes(urllib.request.urlopen(req, timeout=600).read())
    return path


def state_use_2019(key):
    d = pd.read_excel(fetch(key), sheet_name="Data 1", header=2)
    row = d[pd.to_datetime(d["Date"]).dt.year == 2019].iloc[0]
    out = {}
    for col, val in row.items():
        name = str(col).split(" Natural Gas")[0]
        if name in STATES and pd.notna(val):
            out[STATES[name]] = float(val)
    return pd.Series(out)


def demand_weights():
    use = state_use_2019("res").add(state_use_2019("com"), fill_value=0.0)
    rows = []
    for region, ((lat, lon), states) in DEMAND.items():
        rows.append((region, lat, lon, use.reindex(states).fillna(0.0).sum()))
    return pd.DataFrame(rows, columns=["region", "lat", "lon", "raw"])


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dlat, dlon = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def wind_weights(max_km=1000.0):
    z = zipfile.ZipFile(fetch("860"))
    gen = pd.read_excel(z.open("3_2_Wind_Y2019.xlsx"), sheet_name="Operable", header=1)
    plant = pd.read_excel(z.open("2___Plant_Y2019.xlsx"), header=1)
    cap_col = [c for c in gen.columns if str(c).startswith("Nameplate Capacity")][0]
    g = gen.groupby("Plant Code")[cap_col].sum().rename("mw").reset_index()
    g = g.merge(plant[["Plant Code", "State", "Latitude", "Longitude"]], on="Plant Code")
    for c in ("Latitude", "Longitude", "mw"):
        g[c] = pd.to_numeric(g[c], errors="coerce")
    g = g[~g["State"].isin(["AK", "HI"])].dropna(subset=["Latitude", "Longitude", "mw"])
    names = list(WIND)
    dist = np.column_stack([haversine_km(g["Latitude"].values, g["Longitude"].values, *WIND[n])
                            for n in names])
    g["region"] = np.array(names)[dist.argmin(axis=1)]
    g = g[dist.min(axis=1) <= max_km]
    mw = g.groupby("region")["mw"].sum()
    rows = [(n, *WIND[n], float(mw.get(n, 0.0))) for n in names]
    return pd.DataFrame(rows, columns=["region", "lat", "lon", "raw"])


def basin_weights():
    xl = pd.ExcelFile(fetch("dpr"))
    rows = []
    for name, (lat, lon) in BASIN.items():
        d = pd.read_excel(xl, sheet_name=f"{name} Region", header=None, skiprows=2)
        d = d[pd.to_datetime(d[0], errors="coerce").dt.year == 2019]
        rows.append((name, lat, lon, float(d[7].astype(float).mean())))  # gas Mcf/d
    return pd.DataFrame(rows, columns=["region", "lat", "lon", "raw"])


def main():
    parts = []
    for group, df, unit in [("demand", demand_weights(), "MMcf res+com 2019"),
                            ("wind", wind_weights(), "MW nameplate 2019"),
                            ("basin", basin_weights(), "Mcf/d gas 2019 avg")]:
        df["weight"] = df["raw"] / df["raw"].sum()
        df.insert(0, "group", group)
        df["unit"] = unit
        parts.append(df)
    out = pd.concat(parts, ignore_index=True)
    out.to_csv(WEIGHTS_CSV, index=False, float_format="%.6g")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
