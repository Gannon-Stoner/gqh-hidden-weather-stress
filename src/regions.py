"""Fixed region anchors (lat, lon). Each anchor is read as a 3x3 grid-point neighbourhood.

Weights are NOT set here: data/build_weights.py derives them from 2019 EIA data
(pre-sample) and writes data/region_weights.csv.
"""

# Gas-demand anchors and the states whose 2019 residential+commercial use they carry
DEMAND = {
    "BOS": ((42.4, -71.4), ["MA", "CT", "RI", "NH", "VT", "ME"]),
    "NYC": ((40.9, -74.3), ["NY", "NJ"]),
    "PHL": ((40.1, -75.6), ["PA", "DE", "MD", "DC", "VA"]),
    "CMH": ((40.4, -82.6), ["OH", "WV", "KY"]),
    "DET": ((42.6, -83.6), ["MI"]),
    "CHI": ((41.8, -88.1), ["IL", "IN", "WI"]),
    "MSP": ((44.9, -93.4), ["MN", "IA", "ND", "SD"]),
    "MCI": ((38.9, -94.8), ["MO", "KS", "NE", "AR"]),
    "DFW": ((32.9, -97.1), ["TX", "OK", "LA", "NM"]),
    "ATL": ((33.9, -84.4), ["GA", "NC", "SC", "TN", "AL", "MS", "FL"]),
    "DEN": ((39.8, -104.9), ["CO", "UT", "WY", "MT", "ID"]),
    "LAX": ((34.1, -117.9), ["CA", "NV", "AZ"]),
    "SEA": ((47.4, -122.2), ["WA", "OR"]),
}

# Wind anchors; 2019 EIA-860 wind plants are assigned to the nearest anchor
WIND = {
    "WTX": (32.4, -100.4),
    "PAN": (35.4, -101.6),
    "STX": (27.6, -97.9),
    "OKL": (36.2, -98.4),
    "KAN": (38.2, -98.8),
    "IOW": (42.4, -94.3),
    "ILL": (40.6, -88.6),
    "MIN": (44.6, -96.4),
    "WYO": (41.6, -105.6),
    "CAL": (35.1, -118.4),
    "NPC": (45.7, -120.5),
}

# Producing-basin anchors (EIA Drilling Productivity Report regions)
BASIN = {
    "Appalachia": (40.0, -80.3),
    "Permian": (31.9, -102.6),
    "Haynesville": (32.3, -93.8),
    "Eagle Ford": (28.6, -98.6),
    "Anadarko": (35.7, -98.6),
    "Niobrara": (40.4, -104.5),
    "Bakken": (47.9, -103.2),
}
