"""Geography for the simulated portfolio.

The population is India-weighted (the challenge is hosted at GFF Mumbai and the
most interesting live typologies — UPI mule networks, coercion-authorised
"digital arrest" payments — are Indian) with a realistic cross-border tail,
because card-not-present fraud is disproportionately cross-border.
"""

from __future__ import annotations

import math

# (name, country, lat, lon, population weight, tier)
CITIES: list[tuple[str, str, float, float, float, int]] = [
    ("Mumbai",      "IN", 19.0760, 72.8777, 14.0, 1),
    ("Delhi",       "IN", 28.6139, 77.2090, 13.0, 1),
    ("Bengaluru",   "IN", 12.9716, 77.5946, 11.5, 1),
    ("Hyderabad",   "IN", 17.3850, 78.4867,  8.0, 1),
    ("Chennai",     "IN", 13.0827, 80.2707,  7.5, 1),
    ("Kolkata",     "IN", 22.5726, 88.3639,  6.5, 1),
    ("Pune",        "IN", 18.5204, 73.8567,  6.0, 1),
    ("Ahmedabad",   "IN", 23.0225, 72.5714,  5.0, 2),
    ("Jaipur",      "IN", 26.9124, 75.7873,  4.0, 2),
    ("Lucknow",     "IN", 26.8467, 80.9462,  3.4, 2),
    ("Surat",       "IN", 21.1702, 72.8311,  3.2, 2),
    ("Kochi",       "IN",  9.9312, 76.2673,  2.8, 2),
    ("Indore",      "IN", 22.7196, 75.8577,  2.6, 2),
    ("Chandigarh",  "IN", 30.7333, 76.7794,  2.4, 2),
    ("Bhubaneswar", "IN", 20.2961, 85.8245,  2.0, 3),
    ("Guwahati",    "IN", 26.1445, 91.7362,  1.8, 3),
    ("Patna",       "IN", 25.5941, 85.1376,  1.8, 3),
    ("Nagpur",      "IN", 21.1458, 79.0882,  1.7, 3),
    ("Coimbatore",  "IN", 11.0168, 76.9558,  1.6, 3),
    ("Varanasi",    "IN", 25.3176, 82.9739,  1.4, 3),
    # Cross-border tail — legitimate diaspora / travel corridors and, at the
    # other end, the jurisdictions that dominate CNP fraud acquiring.
    ("Dubai",       "AE", 25.2048, 55.2708,  2.2, 1),
    ("Singapore",   "SG",  1.3521, 103.8198, 1.7, 1),
    ("London",      "GB", 51.5074, -0.1278,  1.5, 1),
    ("New York",    "US", 40.7128, -74.0060, 1.4, 1),
    ("Toronto",     "CA", 43.6532, -79.3832, 0.9, 1),
    ("Sydney",      "AU", -33.8688, 151.2093, 0.7, 1),
    ("Hong Kong",   "HK", 22.3193, 114.1694, 0.6, 1),
    ("Lagos",       "NG",  6.5244,  3.3792,  0.4, 3),
    ("Kyiv",        "UA", 50.4501, 30.5234,  0.3, 3),
    ("Manila",      "PH", 14.5995, 120.9842, 0.4, 3),
]

CITY_INDEX = {c[0]: c for c in CITIES}

# Jurisdictions that carry elevated acquiring/beneficiary risk in the model.
HIGH_RISK_COUNTRIES = {"NG", "UA", "PH", "HK"}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(max(0.0, min(1.0, a))))


def jitter_geo(lat: float, lon: float, km: float, rng) -> tuple[float, float]:
    """Displace a point by roughly ``km`` kilometres in a random direction."""
    bearing = rng.uniform(0, 2 * math.pi)
    dlat = (km / 111.0) * math.cos(bearing)
    dlon = (km / (111.0 * max(0.2, math.cos(math.radians(lat))))) * math.sin(bearing)
    return lat + dlat, lon + dlon
