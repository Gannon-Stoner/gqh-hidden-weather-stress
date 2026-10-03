"""Extract member-level gas-day weather features from the dynamical.org GEFS archive.

For every 00 UTC init in Nov-Mar (plus Oct 31) it reads only the zarr chunks that
contain the fixed region anchors, then reduces to:
  T[m, k, anchor]  gas-day mean 2 m temperature (deg C), k = gas-day offset
  CF[m, k, wind]   gas-day mean wind capacity factor from 100 m wind
Per-init results are cached in data/cache/gefs/ (resumable); `--combine` writes the
committed reduced file data/member_features.npz.

Run in a cloud machine (Codespace): python data/build_weather_features.py --workers 8
"""
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C  # noqa: E402
from src.regions import BASIN, DEMAND, WIND  # noqa: E402

CACHE = C.DATA / "cache" / "gefs"
OUT = C.DATA / "member_features.npz"
K_ALL = list(range(2, 15))          # gas-day offsets D+2 ... D+14
K_NEAR_MAX = 6                      # wind / basin anchors only need D+2 ... D+6
LAT_CH, LON_CH, LEAD_CH = 17, 16, 64


def open_ds():
    import icechunk
    import xarray as xr
    st = icechunk.s3_storage(bucket=C.GEFS_BUCKET, prefix=C.GEFS_PREFIX,
                             region=C.GEFS_REGION, anonymous=True)
    return xr.open_zarr(icechunk.Repository.open(st).readonly_session("main").store, chunks=None)


def anchors():
    demand = [(n, ll) for n, (ll, _) in DEMAND.items()]
    return demand, list(WIND.items()), list(BASIN.items())


def gas_day_leads(lead_h, k):
    lo = 24 * k + C.GAS_DAY_START_UTC_HOUR
    return np.where((lead_h >= lo) & (lead_h < lo + 24))[0]


def power_curve(speed, temp_c):
    s = np.asarray(speed)
    pc = np.where((s >= C.CUT_IN) & (s < C.RATED),
                  (s ** 3 - C.CUT_IN ** 3) / (C.RATED ** 3 - C.CUT_IN ** 3), 0.0)
    pc = np.where((s >= C.RATED) & (s < C.CUT_OUT), 1.0, pc)
    derate = np.clip((temp_c - C.DERATE_END_C) / (C.DERATE_START_C - C.DERATE_END_C), 0, 1)
    return pc * derate


class Extractor:
    def __init__(self, ds):
        self.ds = ds
        self.lat, self.lon = ds.latitude.values, ds.longitude.values
        self.lead_h = (ds.lead_time.values / np.timedelta64(1, "h")).astype(int)
        self.demand, self.wind, self.basin = anchors()
        self.idx = {}
        for name, (la, lo) in self.demand + self.wind + self.basin:
            i, j = int(np.abs(self.lat - la).argmin()), int(np.abs(self.lon - lo).argmin())
            self.idx[name] = (i, j)
        self.leads_k = {k: gas_day_leads(self.lead_h, k) for k in K_ALL}

    def _block(self, var, it, names, lead_max_idx, cache):
        """Read the chunk-aligned blocks covering `names` 3x3 neighbourhoods."""
        out = {}
        for name in names:
            i, j = self.idx[name]
            cells = []
            for ii in (i - 1, i, i + 1):
                row = []
                for jj in (j - 1, j, j + 1):
                    key = (var, ii // LAT_CH, jj // LON_CH)
                    if key not in cache or cache[key].shape[1] <= lead_max_idx:
                        ci, cj = key[1], key[2]
                        cache[key] = self.ds[var].isel(
                            init_time=it, latitude=slice(ci * LAT_CH, (ci + 1) * LAT_CH),
                            longitude=slice(cj * LON_CH, (cj + 1) * LON_CH),
                            lead_time=slice(0, lead_max_idx + 1)).values.astype(np.float32)
                    blk = cache[key]
                    row.append(blk[:, :lead_max_idx + 1, ii % LAT_CH, jj % LON_CH])
                cells.append(np.stack(row, -1))
            out[name] = np.stack(cells, -2)          # (member, lead, 3, 3)
        return out

    def run(self, it):
        cache = {}
        lmax_all = int(self.leads_k[max(K_ALL)].max())
        lmax_near = int(self.leads_k[K_NEAR_MAX].max())
        dnames = [n for n, _ in self.demand]
        wnames = [n for n, _ in self.wind]
        bnames = [n for n, _ in self.basin]
        t_dem = self._block("temperature_2m", it, dnames, lmax_all, cache)
        t_near = self._block("temperature_2m", it, wnames + bnames, lmax_near, cache)
        u = self._block("wind_u_100m", it, wnames, lmax_near, cache)
        v = self._block("wind_v_100m", it, wnames, lmax_near, cache)
        names = dnames + wnames + bnames
        m = next(iter(t_dem.values())).shape[0]
        T = np.full((m, len(K_ALL), len(names)), np.nan, np.float32)
        CF = np.full((m, K_NEAR_MAX - 1, len(wnames)), np.nan, np.float32)
        for a, name in enumerate(names):
            src = t_dem.get(name, t_near.get(name))
            for kk, k in enumerate(K_ALL):
                li = self.leads_k[k]
                if li.max() < src.shape[1]:
                    T[:, kk, a] = src[:, li].mean(axis=(1, 2, 3))
        for w, name in enumerate(wnames):
            spd = np.hypot(u[name], v[name])
            pc = power_curve(spd, t_near[name])
            for kk, k in enumerate(range(2, K_NEAR_MAX + 1)):
                CF[:, kk, w] = pc[:, self.leads_k[k]].mean(axis=(1, 2, 3))
        return T, CF, names, wnames


def winter_inits(ds):
    it = pd.to_datetime(ds.init_time.values)
    keep = it.month.isin(C.WINTER_MONTHS) | ((it.month == 10) & (it.day == 31))
    return [(i, t) for i, t in enumerate(it) if keep[i]]


def extract(workers, limit=None, only=None):
    ds = open_ds()
    ex = Extractor(ds)
    CACHE.mkdir(parents=True, exist_ok=True)
    todo = [(i, t) for i, t in winter_inits(ds)
            if not (CACHE / f"{t:%Y%m%d}.npz").exists()]
    if only:
        todo = [(i, t) for i, t in todo if f"{t:%Y-%m-%d}" in only]
    todo = todo[:limit] if limit else todo
    print(f"{len(todo)} inits to extract", flush=True)

    def job(item):
        i, t = item
        t0 = time.time()
        T, CF, names, wnames = ex.run(i)
        np.savez_compressed(CACHE / f"{t:%Y%m%d}.npz", T=T, CF=CF,
                            names=np.array(names), wnames=np.array(wnames))
        return t, time.time() - t0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(job, x) for x in todo]
        for n, f in enumerate(as_completed(futs), 1):
            t, dt = f.result()
            print(f"[{n}/{len(todo)}] {t:%Y-%m-%d} {dt:.1f}s", flush=True)


def combine(out=OUT):
    files = sorted(CACHE.glob("*.npz"))
    dates, Ts, CFs = [], [], []
    for f in files:
        try:
            z = np.load(f)
            z["T"]
        except Exception as e:  # partially written file from a running extraction
            print(f"skip {f.name}: {e}")
            continue
        dates.append(pd.Timestamp(f.stem))
        Ts.append(z["T"])
        CFs.append(z["CF"])
        names, wnames = z["names"], z["wnames"]
    np.savez_compressed(out, init=np.array(dates, dtype="datetime64[D]"),
                        T=np.stack(Ts).astype(np.float32), CF=np.stack(CFs).astype(np.float32),
                        names=names, wnames=wnames, k=np.array(K_ALL))
    print(f"wrote {out} with {len(dates)} inits")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", nargs="*", default=None, help="YYYY-MM-DD init dates")
    ap.add_argument("--combine", action="store_true")
    a = ap.parse_args()
    if a.combine:
        combine()
    else:
        extract(a.workers, a.limit, a.only)
