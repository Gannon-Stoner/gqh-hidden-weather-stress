"""Signals from member-level GEFS features (PREREGISTRATION.md §5).

Input : data/member_features.npz (from data/build_weather_features.py --combine)
        data/region_weights.csv    (from data/build_weights.py)
Output: data/weather_features.csv  (one row per 00 UTC init date; committed)
"""
import numpy as np
import pandas as pd

from src import config as C

K_ALL = np.arange(2, 15)


def winter_of(dates):
    d = pd.DatetimeIndex(dates)
    return np.where(d.month >= 10, d.year, d.year - 1)


def load_members(path=C.DATA / "member_features.npz"):
    z = np.load(path, allow_pickle=False)
    return (pd.DatetimeIndex(z["init"]), z["T"], z["CF"],
            [str(s) for s in z["names"]], [str(s) for s in z["wnames"]])


def weights(names, group):
    w = pd.read_csv(C.WEIGHTS_CSV)
    w = w[w["group"] == group].set_index("region")["weight"]
    idx = [names.index(r) for r in w.index]
    return np.array(idx), w.values


def kslice(lo, hi):
    """Positions in K_ALL for gas-day offsets lo..hi inclusive."""
    return np.where((K_ALL >= lo) & (K_ALL <= hi))[0]


def lowo_quantile(values, months, winters, dev, q):
    """Per-row threshold: q-quantile of `values` (inits x members) over development inits in
    the same calendar month, leaving out the row's own winter. Holdout rows use all dev."""
    out = np.full(len(months), np.nan)
    for i in range(len(months)):
        pool = dev & (months == months[i]) & (winters != winters[i] if dev[i] else True)
        v = values[pool].ravel()
        v = v[np.isfinite(v)]
        if v.size:
            out[i] = np.quantile(v, q)
    return out


def build(path=C.DATA / "member_features.npz"):
    init, T, CF, names, wnames = load_members(path)
    di, dw = weights(names, "demand")
    bi, bw = weights(names, "basin")
    wi, ww = weights(wnames, "wind")

    H = (np.maximum(C.HDD_BASE_C - T[..., di], 0.0) * dw).sum(-1)          # (n, m, k)
    H[np.isnan(T[..., di]).any(-1)] = np.nan
    wk2 = kslice(min(C.WEEK2_DAYS), max(C.WEEK2_DAYS))
    Hbar = H[:, :, wk2].mean(-1)                                           # (n, m)

    months, winters = init.month.values, winter_of(init)
    dev = (init < pd.Timestamp(C.HOLDOUT_START)) & np.isin(months, C.WINTER_MONTHS)
    hold = init >= pd.Timestamp(C.HOLDOUT_START)

    tau_hi = lowo_quantile(Hbar, months, winters, dev, C.TAIL_QUANTILE)
    tau_lo = lowo_quantile(Hbar, months, winters, dev, 1 - C.TAIL_QUANTILE)
    valid = np.isfinite(Hbar)
    nm = valid.sum(1)
    p_cold = np.where(valid, Hbar > tau_hi[:, None], False).sum(1) / np.maximum(nm, 1)
    p_warm = np.where(valid, Hbar < tau_lo[:, None], False).sum(1) / np.maximum(nm, 1)
    p_cold[~np.isfinite(tau_hi)] = np.nan
    p_warm[~np.isfinite(tau_lo)] = np.nan

    a = np.nanmean(Hbar, 1)
    a_hi = lowo_quantile(a[:, None], months, winters, dev, C.TAIL_QUANTILE)
    mu = pd.Series(a[dev]).groupby(months[dev]).mean()
    sd = pd.Series(a[dev]).groupby(months[dev]).std()
    a_z = (a - mu.reindex(months).values) / sd.reindex(months).values

    # Co-stress dependence over gas days D+2..D+6 (per offset), then same-valid-day revision
    near = kslice(2, 6)
    x = H[:, :, near]                                                      # (n, m, 5)
    y = 1.0 - (CF[..., wi] * ww).sum(-1)                                   # (n, m, 5)
    xc, yc = x - np.nanmean(x, 1, keepdims=True), y - np.nanmean(y, 1, keepdims=True)
    cov_k = np.nanmean(xc * yc, 1)                                         # (n, 5) offsets 2..6
    corr_k = cov_k / (np.nanstd(x, 1) * np.nanstd(y, 1))
    K_new = cov_k[:, 0:4].mean(1)                                          # offsets 2..5
    rho = np.nanmean(corr_k[:, 0:4], 1)
    prev = pd.Series(np.arange(len(init)), index=init)
    j = prev.reindex(init - pd.Timedelta(days=1)).values                   # yesterday's init
    K_old = np.full(len(init), np.nan)
    ok = np.isfinite(j)
    K_old[ok] = cov_k[j[ok].astype(int), 1:5].mean(1)                     # offsets 3..6 = same days

    fit = dev & np.isfinite(K_new) & np.isfinite(K_old)
    b_hat = np.polyfit(K_old[fit], K_new[fit], 1)[0] if fit.sum() > 10 else np.nan
    dK_star = K_new - b_hat * K_old

    Bm = (np.maximum(C.FREEZE_BASE_C - T[..., bi], 0.0) * bw).sum(-1)      # (n, m, k)
    B = np.nanmean(Bm[:, :, kslice(2, 5)], axis=(1, 2))

    f = pd.DataFrame({
        "init": init, "winter": winters, "is_dev": dev, "is_holdout": hold, "n_members": nm,
        "a": a, "a_z": a_z, "a_hi": a_hi, "b1_signal": a > a_hi,
        "tau_hi": tau_hi, "p_cold": p_cold, "p_warm": p_warm,
        "K": K_new, "K_old": K_old, "dK_star": dK_star, "rho": rho, "B": B,
    }).set_index("init")
    for col in ("a", "p_cold", "B"):
        prev_val = f[col].reindex(f.index - pd.Timedelta(days=1)).values
        f[f"d_{col}"] = f[col].values - prev_val
    f.attrs["b_hat"] = b_hat
    return f


def save(f, path=C.FEATURES_CSV):
    f.to_csv(path, float_format="%.6g")
    print(f"wrote {path}: {len(f)} inits, b_hat={f.attrs.get('b_hat'):.3f}")


def load_features(path=C.FEATURES_CSV):
    return pd.read_csv(path, index_col="init", parse_dates=["init"])


if __name__ == "__main__":
    save(build())
