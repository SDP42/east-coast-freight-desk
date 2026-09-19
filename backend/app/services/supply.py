"""Ship availability at the main coking-coal loading region, from a real public feed.

Source: Port Authority of NSW "Newcastle Harbour daily vessel movements" (public web page). Newcastle is the world's
largest coal port. Each row is an arrival or departure with the vessel's name, type, last or next port and berth.
We treat a bulk carrier that is arriving from an Asian or other non-coal port as OPEN TONNAGE about to load (it comes
in empty), and count bulk carriers due in the next seven days as the supply signal for Australian cargoes.

Limits, stated in the response: the feed gives no deadweight or draft, so ships are not matched by size; it covers
Newcastle only (Hay Point, Abbot Point and Richards Bay are not read); and the page terms on reuse were not confirmed,
so raw rows are shown as a live view and cached for 30 minutes, not stored.
"""

import re
import time
import urllib.request
from datetime import datetime

URL = "https://www.portauthoritynsw.com.au/port-operations/newcastle-harbour/newcastle-harbour-daily-vessel-movements"
CACHE_SECONDS = 1800
COAL_BERTH_HINTS = ("Kooragang", "Carrington")  # NCIG and PWCS coal terminals; Dyke, Mayfield and Walsh Point are general cargo
_cache: dict = {"at": 0.0, "rows": [], "error": None}


def _clean(html_fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html_fragment)
    text = text.replace("&amp;", "&").replace("&#039;", "'")
    return re.sub(r"\s+", " ", text).strip()


def _parse(html: str) -> list[dict]:
    html = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S):
        cells = [_clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
        if len(cells) < 9 or cells[0].startswith("Date"):
            continue
        rows.append({
            "when": cells[0], "movement": cells[2], "vessel": cells[3], "vessel_type": cells[4], "agent": cells[5],
            "from": cells[6], "to": cells[7], "in_port": cells[8].lower() == "yes",
        })
    return rows


def movements(force: bool = False) -> dict:
    now = time.time()
    if not force and _cache["rows"] and now - _cache["at"] < CACHE_SECONDS:
        return {"rows": _cache["rows"], "fetched_at": _cache["at"], "error": None, "stale": False}
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (freight-desk research prototype)"})
        rows = _parse(urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore"))
        if rows:
            _cache.update(at=now, rows=rows, error=None)
        else:
            _cache["error"] = "The page returned no movements."
    except Exception as e:  # noqa: BLE001 - network or page change; fall back to the last good copy
        _cache["error"] = f"{type(e).__name__}: {e}"
    return {"rows": _cache["rows"], "fetched_at": _cache["at"], "error": _cache["error"], "stale": bool(_cache["error"])}


def _is_bulk(v: dict) -> bool:
    return "bulk" in v["vessel_type"].lower() or "open hatch" in v["vessel_type"].lower()


def newcastle_supply() -> dict:
    feed = movements()
    rows = feed["rows"]
    bulk = [r for r in rows if _is_bulk(r)]
    arrivals = [r for r in bulk if r["movement"].lower().startswith("arr")]
    departures = [r for r in bulk if r["movement"].lower().startswith("dep")]
    in_port = [r for r in bulk if r["in_port"]]
    # An arrival whose last port is not Newcastle/Australia is a ship coming in to load (open tonnage).
    def coming_in_to_load(r: dict) -> bool:
        return r["movement"].lower().startswith("arr") and any(h in r["to"] for h in COAL_BERTH_HINTS)

    open_ships = [r for r in arrivals if coming_in_to_load(r)]
    origins: dict[str, int] = {}
    for r in open_ships:
        origins[r["from"]] = origins.get(r["from"], 0) + 1
    coal_deps = [r for r in departures if any(h in r["from"] for h in COAL_BERTH_HINTS)]
    n_arr, n_dep = len(open_ships), len(coal_deps)
    if n_arr >= n_dep * 1.15 + 2:
        signal, meaning = "Tonnage building", "More bulk carriers are arriving at the coal berths than are leaving loaded, so ships are plentiful for Australian cargoes; rates tend to soften."
    elif n_dep >= n_arr * 1.15 + 2:
        signal, meaning = "Tonnage thinning", "More coal ships are leaving loaded than are arriving, so fewer ships are open at the loading port; expect firmer rates and book early."
    else:
        signal, meaning = "Balanced", "Arrivals and departures are close, so there is no clear tightness in Australian tonnage."
    return {
        "source": "Port Authority of NSW, Newcastle Harbour daily vessel movements (public page)", "url": URL,
        "fetched_at": datetime.fromtimestamp(feed["fetched_at"]).isoformat(timespec="seconds") if feed["fetched_at"] else None,
        "error": feed["error"], "stale": feed["stale"],
        "window_movements": len(rows), "bulk_movements": len(bulk),
        "bulk_arrivals": len(arrivals), "bulk_departures": len(departures), "bulk_in_port_now": len(in_port),
        "open_ships_arriving": n_arr, "coal_cargoes_loaded": n_dep,
        "arriving_from": sorted(({"port": k, "ships": v} for k, v in origins.items()), key=lambda x: -x["ships"])[:8],
        "signal": signal, "meaning": meaning,
        "arrivals": open_ships[:25],
        "limits": "No deadweight or draft in the feed, so ships are not matched by size. Newcastle only. Reuse terms of the source page not confirmed, so rows are a live view, cached for 30 minutes, not stored.",
    }
