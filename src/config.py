"""Constants frozen by PREREGISTRATION.md. Changing any value is a logged amendment."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RESULTS = ROOT / "results"
FEATURES_CSV = DATA / "weather_features.csv"     # committed, derived from CC BY 4.0 GEFS
WEIGHTS_CSV = DATA / "region_weights.csv"        # committed, derived from EIA (public)

# Weather archive (dynamical.org, CC BY 4.0)
GEFS_BUCKET = "dynamical-noaa-gefs"
GEFS_PREFIX = "noaa-gefs-forecast-35-day/v0.2.0.icechunk/"
GEFS_REGION = "us-west-2"
WEATHER_VARS = ("temperature_2m", "wind_u_100m", "wind_v_100m")
ARCHIVE_START = "2020-10-01"

# Gas day = 15 UTC to 15 UTC; windows are gas-day offsets from the init date D
GAS_DAY_START_UTC_HOUR = 15
WEEK2_DAYS = range(6, 15)       # D+6 ... D+14, tail-probability window
NEAR_DAYS = range(2, 6)         # D+2 ... D+5, co-stress K and basin cold
HDD_BASE_C = 18.0
FREEZE_BASE_C = 0.0
TAIL_QUANTILE = 0.90
P_COLD_ENTRY = 0.30
WINTER_MONTHS = (11, 12, 1, 2, 3)

# Generic wind power curve (m/s) and cold derate (deg C)
CUT_IN, RATED, CUT_OUT = 3.0, 12.0, 25.0
DERATE_START_C, DERATE_END_C = -20.0, -30.0

# Trading rule
HOLD_SESSIONS = 5
EXPIRY_BUFFER_SESSIONS = 2
NAV = 1_000_000.0
RISK_FRACTION = 0.01
MAX_SPREADS = 25
EWMA_LAMBDA = 0.94
VOL_LOOKBACK = 60
STOP_FRACTION = 0.03
MULTIPLIER = 10_000           # MMBtu per NG contract
TICK = 0.001                  # $/MMBtu, = $10 per contract
FEE_PER_LEG_SIDE = 2.50
SLIP_TICKS_PER_LEG_SIDE = 1.0

# Development / holdout split (min(20% of history, 2 years) of 2020-10-01..2026-10-03)
HOLDOUT_START = "2025-07-22"
DATA_END = "2026-10-03"
