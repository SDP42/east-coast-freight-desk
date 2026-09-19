"""Weather-window planner for a port: the next seven days of waves, wind and rain, turned into working days for berthing and coal handling.

Data: Open-Meteo marine and forecast APIs (free, no key; CC BY 4.0, free for non-commercial use, attribution required). Fetched live
and cached three hours, never stored. The thresholds are ASSUMED planning values, not port rules; the ports' own limits govern.
"""

import json
import time
import urllib.request
from datetime import date

from sqlalchemy.orm import Session

from app.models import Port

WAVE_RED_M, WAVE_AMBER_M = 2.5, 1.8   # significant wave height: pilotage and berthing likely suspended above red
GUST_RED_KN, GUST_AMBER_KN = 34.0, 25.0  # gusts: grab and crane work usually stops near the red level
RAIN_RED_MM, RAIN_AMBER_MM = 100.0, 50.0  # daily rain: coal handling slows or stops
WORK_SHARE = {"green": 1.0, "amber": 0.7, "red": 0.25}
_cache: dict[str, tuple[float, dict]] = {}


def _get(url: str) -> dict:
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "freight-desk-research/1.0"}), timeout=25).read())


def _level(v: float, amber: float, red: float) -> str:
    return "red" if v >= red else "amber" if v >= amber else "green"


def window(db: Session, port_name: str) -> dict:
    port = db.query(Port).filter(Port.name == port_name, Port.is_destination.is_(True)).first()
    if port is None or port.latitude is None:
        raise ValueError(f"Unknown port {port_name}")
    hit = _cache.get(port_name)
    if hit and time.time() - hit[0] < 10800:
        return hit[1]
    lat, lon = float(port.latitude), float(port.longitude)
    tz = "Asia%2FKolkata"
    marine = _get(f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&daily=wave_height_max,wave_period_max&forecast_days=7&timezone={tz}")["daily"]
    wx = _get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=wind_speed_10m_max,wind_gusts_10m_max,precipitation_sum&wind_speed_unit=kn&forecast_days=7&timezone={tz}")["daily"]
    days = []
    for i, d in enumerate(marine["time"]):
        wave = marine["wave_height_max"][i]
        gust = wx["wind_gusts_10m_max"][i]
        rain = wx["precipitation_sum"][i]
        if wave is None:  # river ports such as Haldia have no open-sea wave data
            wave = 0.0
        lv = {"waves": _level(wave, WAVE_AMBER_M, WAVE_RED_M), "wind": _level(gust, GUST_AMBER_KN, GUST_RED_KN), "rain": _level(rain, RAIN_AMBER_MM, RAIN_RED_MM)}
        worst = "red" if "red" in lv.values() else "amber" if "amber" in lv.values() else "green"
        reasons = [f"{k} {lv[k]}" for k in lv if lv[k] != "green"]
        days.append({"date": d, "wave_m": wave, "wave_period_s": marine["wave_period_max"][i], "gust_kn": gust, "wind_kn": wx["wind_speed_10m_max"][i], "rain_mm": rain,
                     "levels": lv, "status": worst, "workable_share": WORK_SHARE[worst], "why": reasons})
    best = None
    for i in range(len(days) - 2):
        s = sum(x["workable_share"] for x in days[i:i + 3])
        if best is None or s > best[0]:
            best = (s, i)
    lost = round(sum(1 - x["workable_share"] for x in days), 1)
    red_days = [x["date"] for x in days if x["status"] == "red"]
    if not red_days and lost < 1:
        headline = f"Clear week at {port_name}: berthing and handling should run normally."
    elif red_days:
        headline = f"{port_name}: {len(red_days)} day(s) likely lost to weather (from {red_days[0]}); about {lost} working days lost this week. Delay arrivals and pilotage accordingly."
    else:
        headline = f"{port_name}: some slowdown expected (about {lost} working days lost this week), no full stoppage forecast."
    out = {
        "port": port_name, "as_of": date.today().isoformat(), "days": days, "lost_working_days": lost, "red_days": red_days, "headline": headline,
        "best_three_day_window": {"from": days[best[1]]["date"], "to": days[best[1] + 2]["date"], "workable_days": round(best[0], 1)} if best else None,
        "thresholds": {"wave_m": [WAVE_AMBER_M, WAVE_RED_M], "gust_kn": [GUST_AMBER_KN, GUST_RED_KN], "rain_mm": [RAIN_AMBER_MM, RAIN_RED_MM]},
        "note": "Thresholds are assumed planning values, not the port's rules. Wave data is for open water near the port and is not available for river berths such as Haldia. Weather data: Open-Meteo.com (CC BY 4.0), fetched live, not stored.",
    }
    _cache[port_name] = (time.time(), out)
    return out
