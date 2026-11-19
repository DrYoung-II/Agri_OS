"""
weather.py
Free, keyless weather + geocoding via Open-Meteo (https://open-meteo.com).
No API key, no billing - perfect for a free test-run deployment.
"""

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 8


def geocode_location(place_name: str):
    """Return (lat, lon, display_name) for a place, or (None, None, None) if not found."""
    try:
        r = requests.get(GEOCODE_URL, params={"name": place_name, "count": 1}, timeout=TIMEOUT)
        if r.status_code == 200:
            results = r.json().get("results")
            if results:
                res = results[0]
                display = f"{res.get('name')}, {res.get('admin1', '')} {res.get('country', '')}".strip()
                return res["latitude"], res["longitude"], display
    except requests.exceptions.RequestException:
        pass
    return None, None, None


def get_forecast(lat: float, lon: float, days: int = 7):
    """Return a dict with daily forecast arrays, or None if the request fails."""
    try:
        r = requests.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,relative_humidity_2m_mean",
                "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
                "timezone": "auto",
                "forecast_days": days,
            },
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()
    except requests.exceptions.RequestException:
        pass
    return None


def farming_risk_notes(forecast: dict):
    """Turn raw forecast numbers into plain-language agronomic risk flags."""
    notes = []
    if not forecast:
        return ["Weather data unavailable right now - check your internet connection."]

    daily = forecast.get("daily", {})
    tmax = daily.get("temperature_2m_max", [])
    rain = daily.get("precipitation_sum", [])
    wind = daily.get("wind_speed_10m_max", [])

    if tmax and max(tmax) >= 35:
        notes.append("🔥 High heat stress risk for poultry/livestock in the coming days (>35°C). "
                      "Ensure extra water and ventilation/shade.")
    if rain and sum(rain) >= 60:
        notes.append("🌧️ Heavy rainfall expected this week - risk of waterlogging, fungal crop "
                      "disease, and flooded pens/pastures. Check drainage.")
    if rain and sum(rain) < 5:
        notes.append("☀️ Very low rainfall expected - drought/irrigation risk for rain-fed crops "
                      "over the coming week.")
    if wind and max(wind) >= 40:
        notes.append("💨 Strong winds forecast - secure poultry housing, greenhouse covers, and "
                      "young plants.")
    if not notes:
        notes.append("✅ No major weather risk flags for the coming week - conditions look "
                      "broadly favourable.")
    return notes
