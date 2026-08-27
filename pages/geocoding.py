"""Geocoding via OpenStreetMap's Nominatim service.

Used to look up (latitude, longitude) for a Location the first time
it's created, so properties can be plotted on the map view without
realtors ever having to enter coordinates themselves.

This is called rarely (once per unique city/area, not once per
property -- Location is a shared model reused across many listings),
which keeps well within Nominatim's usage policy for their free
public endpoint: max 1 request/second, light/occasional use only,
proper attribution required. See:
https://operations.osmfoundation.org/policies/nominatim/

If this project ever needed frequent or bulk geocoding, their policy
points to paid alternatives instead -- this module is intentionally
built to fail silently and never block saving a Location, since
geocoding is a nice-to-have for the map view, not a requirement for
the core listing flow to work.
"""

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Nominatim's usage policy requires a real identifying User-Agent --
# generic/default User-Agents set by HTTP libraries are explicitly
# not accepted and can get requests blocked.
USER_AGENT = "EST-MGT-RealEstatePlatform/1.0 (contact: info@est-mgt.com)"


def geocode_address(query):
    """Look up (latitude, longitude) for a free-text place name.
    Returns None on any failure (network error, timeout, no
    results) rather than raising."""
    try:
        response = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=5,
        )
        response.raise_for_status()
        results = response.json()
    except (requests.RequestException, ValueError):
        return None

    if not results:
        return None

    try:
        return float(results[0]["lat"]), float(results[0]["lon"])
    except (KeyError, TypeError, ValueError):
        return None