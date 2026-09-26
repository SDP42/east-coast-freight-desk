"""Live weather and sea state at the East Coast discharge ports.

Source: Open-Meteo (https://open-meteo.com): the forecast API for wind, rain and temperature and the marine API for wave height. It
needs no account or key and is free for non-commercial use, with attribution (CC BY 4.0). Both are called once for all ports.

The 'working risk' label is our own simple rule, not a forecast product: it flags days when strong gusts or high waves usually stop
cargo work or pilotage. The limits are named below and returned with the answer so they can be changed."""

import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.cache import cached
from app.models import Port

log = logging.getLogger("app.weather")
UA = {"User-Agent": "Mozilla/5.0 (freight-desk research prototype)", "Accept": "application/json"}
TIMEOUT = 12
CACHE_SECONDS = 1800
FORECAST = "https://api.open-meteo.com/v1/forecast"
MARINE = "https://marine-api.open-meteo.com/v1/marine"
DAYS = 5
# Assumed operating limits (named, so a reader can challenge them): gust in km/h, wave height in metres.
LIMITS = {"gust_moderate_kmh": 40.0, "gust_high_kmh": 55.0, "wave_moderate_m": 1.5, "wave_high_m": 2.5}
WMO = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
       61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
       80: "Rain showers", 81: "Rain showers", 82: "Violent showers", 95: "Thunderstorm", 96: "Thunderstorm, hail", 99: "Thunderstorm, hail"}


def _get_json(url: str):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=TIMEOUT).read().decode())


def _query(base: str, coords: list[tuple[float, float]], extra: dict) -> list[dict]:
    q = {"latitude": ",".join(f"{a:.4f}" for a, _ in coords), "longitude": ",".join(f"{b:.4f}" for _, b in coords),
         "timezone": "Asia/Kolkata", "forecast_days": DAYS, **extra}
    j = _get_json(f"{base}?{urllib.parse.urlencode(q, safe=',')}")
    return j if isinstance(j, list) else [j]


def fetch_weather(coords: list[tuple[float, float]]) -> list[dict]:
    return _query(FORECAST, coords, {"current": "temperature_2m,wind_speed_10m,wind_gusts_10m,weather_code,precipitation", "wind_speed_unit": "kmh",
                                     "daily": "wind_gusts_10m_max,precipitation_sum,weather_code"})


def fetch_marine(coords: list[tuple[float, float]]) -> list[dict]:
    return _query(MARINE, coords, {"daily": "wave_height_max"})


def working_risk(gust_kmh: float | None, wave_m: float | None) -> str:
    g, w = gust_kmh or 0.0, wave_m or 0.0
    if g >= LIMITS["gust_high_kmh"] or w >= LIMITS["wave_high_m"]:
        return "High"
    if g >= LIMITS["gust_moderate_kmh"] or w >= LIMITS["wave_moderate_m"]:
        return "Moderate"
    return "Low"


def build(ports: list[tuple[str, float, float]]) -> dict:
    """ports: (name, latitude, longitude). Pure function of the two fetch calls, so it can be tested without a network."""
    if not ports:
        return {"available": True, "ports": []}
    coords = [(a, b) for _, a, b in ports]
    fc = fetch_weather(coords)
    try:
        mar = fetch_marine(coords)
    except Exception as e:  # sea state is optional: wind and rain are still useful
        log.warning("Marine data unavailable: %s", e)
        mar = [{} for _ in ports]
    out = []
    for (name, lat, lon), f, m in zip(ports, fc, mar):
        cur, day = f.get("current", {}), f.get("daily", {})
        waves = (m.get("daily") or {}).get("wave_height_max") or []
        days = []
        for i, d in enumerate(day.get("time", [])):
            g = (day.get("wind_gusts_10m_max") or [None] * 9)[i]
            w = waves[i] if i < len(waves) else None
            days.append({"date": d, "gust_max_kmh": g, "rain_mm": (day.get("precipitation_sum") or [None] * 9)[i], "wave_max_m": w,
                         "summary": WMO.get((day.get("weather_code") or [None] * 9)[i], "Mixed"), "working_risk": working_risk(g, w)})
        worst = max(days, key=lambda x: {"Low": 0, "Moderate": 1, "High": 2}[x["working_risk"]], default=None)
        out.append({"port": name, "latitude": lat, "longitude": lon,
                    "now": {"time": cur.get("time"), "temperature_c": cur.get("temperature_2m"), "wind_kmh": cur.get("wind_speed_10m"),
                            "gust_kmh": cur.get("wind_gusts_10m"), "rain_mm": cur.get("precipitation"),
                            "summary": WMO.get(cur.get("weather_code"), "Mixed"),
                            "working_risk": working_risk(cur.get("wind_gusts_10m"), waves[0] if waves else None)},
                    "days": days, "worst_day": worst})
    return {"available": True, "ports": out, "limits": LIMITS, "source": "Open-Meteo (forecast and marine APIs), CC BY 4.0",
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": "Working risk is a simple rule on gusts and wave height (limits shown), not an official forecast. Wave data is offshore, so it can overstate river ports."}


def port_weather(db: Session, scope: list[str] | None) -> dict:
    rows = db.query(Port).filter(Port.is_destination.is_(True), Port.latitude.isnot(None), Port.longitude.isnot(None)).order_by(Port.name).all()
    ports = [(p.name, float(p.latitude), float(p.longitude)) for p in rows if scope is None or p.name in scope]
    key = "weather:" + ",".join(n for n, _, _ in ports)
    try:
        return cached(key, CACHE_SECONDS, lambda: build(ports))
    except Exception as e:
        log.warning("Weather unavailable: %s", e)
        return {"available": False, "ports": [], "note": "The weather service could not be reached just now. Try again in a minute."}
