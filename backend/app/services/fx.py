"""Live USD to INR rate and a converter.

Source: the Frankfurter service (https://frankfurter.dev), which republishes the European Central Bank's euro foreign exchange
reference rates. It needs no account or key. The ECB publishes once each business day (about 16:00 Central European Time), so 'today'
means the latest business day and the response carries that date. There is no free source of minute-level currency quotes.

If Frankfurter cannot be reached the answer falls back to the Federal Reserve series already stored (FRED, INR per USD), clearly
labelled with its own older date, so the page never shows a rate without saying where it is from and how old it is.

The cost model elsewhere in the app keeps using the stored Federal Reserve rate so that every rupee figure stays reproducible; that
rate is returned here as `model_rate` so a reader can see both."""

import json
import logging
import urllib.request
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cache import cached
from app.models import FreightRate

log = logging.getLogger("app.fx")
BASE = "https://api.frankfurter.dev/v1"
UA = {"User-Agent": "Mozilla/5.0 (freight-desk research prototype)", "Accept": "application/json"}
TIMEOUT = 8
SOURCE = "European Central Bank reference rate, via Frankfurter (frankfurter.dev)"
CACHE_SECONDS = 900


def _get_json(url: str) -> dict:
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=TIMEOUT).read().decode())


def fetch_latest() -> tuple[float, str]:
    """(INR per USD, date the rate applies to)."""
    j = _get_json(f"{BASE}/latest?base=USD&symbols=INR")
    return float(j["rates"]["INR"]), str(j["date"])


def fetch_history(days: int = 30) -> list[dict]:
    end = date.today()
    j = _get_json(f"{BASE}/{end - timedelta(days=days)}..{end}?base=USD&symbols=INR")
    return [{"date": d, "inr_per_usd": float(v["INR"])} for d, v in sorted(j.get("rates", {}).items())]


def stored_rate(db: Session) -> dict | None:
    """The Federal Reserve INR per USD stored by the data refresh (what every cost in the app is converted with)."""
    latest = db.query(func.max(FreightRate.rate_date)).filter(FreightRate.index_name == "INR").scalar()
    if latest is None:
        return None
    row = db.query(FreightRate).filter(FreightRate.index_name == "INR", FreightRate.rate_date == latest).first()
    return {"rate": round(float(row.value), 4), "date": str(latest), "source": "Federal Reserve (FRED DEXINUS), stored"}


def _build(db: Session) -> dict:
    model = stored_rate(db)
    out: dict = {"base": "USD", "quote": "INR", "model_rate": model, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        rate, day = fetch_latest()
        out.update(rate=round(rate, 4), rate_date=day, source=SOURCE, live=True, inr_per_usd=round(rate, 4), usd_per_inr=round(1 / rate, 6))
        try:
            out["history"] = fetch_history(30)
        except Exception as e:  # the sparkline is optional
            log.warning("FX history unavailable: %s", e)
            out["history"] = []
    except Exception as e:
        log.warning("Live FX unavailable, using stored rate: %s", e)
        if model is None:
            return {**out, "live": False, "rate": None, "rate_date": None, "source": None, "history": [],
                    "note": "The live rate could not be fetched and no stored rate exists."}
        out.update(rate=model["rate"], rate_date=model["date"], source=model["source"], live=False, inr_per_usd=model["rate"],
                   usd_per_inr=round(1 / model["rate"], 6), history=[],
                   note="The live source could not be reached, so this is the last stored Federal Reserve rate, dated as shown.")
    if out.get("live") and model:
        out["difference_vs_model_pct"] = round((out["rate"] / model["rate"] - 1) * 100, 2)
    out.setdefault("note", "ECB reference rates are published once per business day; on weekends and holidays the latest business day is shown.")
    return out


def live_rate(db: Session) -> dict:
    """Cached for 15 minutes. A failed live fetch is cached for a shorter time so it is retried soon."""
    key = f"fx:usdinr:{date.today()}"
    res = cached(key, CACHE_SECONDS, lambda: _build(db))
    if not res.get("live"):
        # do not keep serving a fallback for the full window: try again on the next request after a minute
        from app.core.cache import _set  # noqa: PLC0415

        _set(key, 60, json.dumps(res, default=str))
    return res


def convert(amount: float, from_ccy: str, rate: float) -> dict:
    """Convert between USD and INR with the given INR-per-USD rate."""
    f = from_ccy.upper()
    if f not in ("USD", "INR"):
        raise ValueError("Only USD and INR are supported")
    if rate <= 0:
        raise ValueError("The rate must be positive")
    if f == "USD":
        return {"from": "USD", "to": "INR", "amount": amount, "result": round(amount * rate, 2), "rate": rate}
    return {"from": "INR", "to": "USD", "amount": amount, "result": round(amount / rate, 4), "rate": rate}
