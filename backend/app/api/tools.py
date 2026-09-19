"""API for the second feature batch: signals, voyage economics, ledger, monitoring, alerts, explorer, briefing."""

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require, require_port
from app.core.permissions import PORT_ALERT_KINDS, has, permissions_of as has_perms, port_scope, role_of
from app.core.cache import cached, data_version
from app.db.session import get_db
from app.models import AlertEvent, AlertRule, LedgerEntry, Port, User
from app.services import alerts as alert_service
from app.services import briefing, explorer, ledger, monitor, signals, voyage
from app.services.quick_forecast import quick_forecast
from app.services.recommendation import pareto_rank

router = APIRouter(tags=["tools"])

DEST_ORIGINS = ["Australia", "United States", "Mozambique", "Russia", "Indonesia"]


def _bad(exc: Exception) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


# ------------------------------------------------------------------ signals
@router.get("/signals/cyclone", dependencies=[Depends(require("ports:read"))])
def cyclone(port: str, laycan_start: date, laycan_end: date, transit_days: float = 0.0, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    require_port(user, port, db)
    if laycan_end < laycan_start or (laycan_end - laycan_start).days > 120:
        raise HTTPException(status_code=422, detail="laycan window must be 0-120 days")
    try:
        return signals.cyclone_eta_risk(db, port, laycan_start, laycan_end, transit_days)
    except ValueError as exc:
        raise _bad(exc)


@router.get("/signals/berth-slots", dependencies=[Depends(require("ports:read"))])
def berth_slots(port: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    require_port(user, port, db)
    try:
        return cached(f"slots:{port}:{data_version(db, 'BPI')}:{date.today()}", 3600, lambda: signals.berth_slots(db, port))
    except ValueError as exc:
        raise _bad(exc)


@router.get("/signals/transfer", dependencies=[Depends(require("ports:read"))])
def transfer(db: Session = Depends(get_db), user: User | None = Depends(get_current_user)) -> dict:
    data = cached(f"transfer:{date.today()}", 3600, lambda: signals.congestion_transfer(db))
    scope = port_scope(user) if user is not None else None
    if scope is None:
        return data
    # Port-scoped roles see only their own ports: other ports' figures are removed, not just hidden in the UI.
    inside = lambda p: p in scope  # noqa: E731
    return {**data, "pairs": [p for p in data["pairs"] if inside(p["from_port"]) and inside(p["to_port"])],
            "significant_pairs": [p for p in data["significant_pairs"] if inside(p["from_port"]) and inside(p["to_port"])],
            "status": [s_ for s_ in data["status"] if inside(s_["port"])],
            "signal": data["signal"] if data["signal"] and inside(data["signal"]["hot_port"]) and (data["signal"].get("consider") is None or inside(data["signal"]["consider"])) else None,
            "scope_note": f"Showing only your assigned ports: {', '.join(scope) or 'none assigned'}."}


@router.get("/signals/demand", dependencies=[Depends(require("demand:read"))])
def demand(growth_pct: float = Query(0, ge=-30, le=30), parcel_tonnes: float = Query(33000, ge=5000, le=200000)) -> dict:
    return signals.demand_estimate(growth_pct, parcel_tonnes)


# ------------------------------------------------------------------ forecasting extras
@router.get("/forecast-multi/{index_name}", dependencies=[Depends(require("market:read"))])
def forecast_multi(index_name: str, db: Session = Depends(get_db)) -> dict:
    name = index_name.upper()
    return cached(f"multi:{name}:{data_version(db, name)}", 6 * 3600, lambda: _multi(name, db))


def _multi(index_name: str, db: Session) -> dict:
    out = []
    for h in (7, 14, 30, 60, 90):
        f = quick_forecast(db, index_name.upper(), h)
        if f is None:
            raise HTTPException(status_code=404, detail=f"Not enough history for {index_name}")
        out.append({"horizon": h, "value": round(f.forecast_end, 2), "change_pct": round(f.change_pct, 2), "lower": round(f.lower, 2), "upper": round(f.upper, 2)})
    return {"index_name": index_name.upper(), "last_date": f.last_date, "last_value": round(f.last_value, 2), "horizons": out,
            "note": "ARIMA(2,1,2) fitted on the latest ~3 years. Bands widen quickly: at 60-90 days they are wide enough that direction is barely informative."}


class ParetoRequest(BaseModel):
    destination_port_id: int
    cargo_tonnes: float = Field(gt=0)
    w_cost: float = Field(0.5, ge=0)
    w_time: float = Field(0.25, ge=0)
    w_risk: float = Field(0.25, ge=0)


@router.post("/recommendation/pareto", dependencies=[Depends(require("recommend:read"))])
def pareto(p: ParetoRequest, db: Session = Depends(get_db)) -> dict:
    port = db.query(Port).filter(Port.id == p.destination_port_id).first()
    if not port:
        raise HTTPException(status_code=404, detail="Port not found")
    total = (p.w_cost + p.w_time + p.w_risk) or 1.0
    return pareto_rank(db, port, p.cargo_tonnes, DEST_ORIGINS, (p.w_cost / total, p.w_time / total, p.w_risk / total))


# ------------------------------------------------------------------ voyage economics
class CarbonRequest(BaseModel):
    vessel_class: str
    distance_nm: float = Field(gt=0, le=25000)
    speed_knots: float = Field(12.0, ge=8, le=16)
    fuel: str = "VLSFO"
    year: int = Field(2026, ge=2023, le=2026)
    include_ballast_return: bool = True
    cargo_tonnes: float | None = Field(None, gt=0)


@router.post("/voyage/carbon", dependencies=[Depends(require("recommend:read"))])
def carbon(p: CarbonRequest, db: Session = Depends(get_db)) -> dict:
    if p.fuel not in voyage.CO2_T_PER_T_FUEL:
        raise HTTPException(status_code=422, detail=f"fuel must be one of {list(voyage.CO2_T_PER_T_FUEL)}")
    try:
        return voyage.carbon_estimate(db, p.vessel_class, p.distance_nm, p.speed_knots, p.fuel, p.year, p.include_ballast_return, p.cargo_tonnes)
    except ValueError as exc:
        raise _bad(exc)


class HedgeRequest(BaseModel):
    usd_cost: float = Field(gt=0)
    months: int = Field(6, ge=1, le=24)
    hedge_ratio_pct: float = Field(25, ge=0, le=100)
    inr_rate_pct: float = Field(6.5, ge=0, le=20)
    usd_rate_pct: float = Field(4.3, ge=0, le=20)


@router.post("/voyage/hedge", dependencies=[Depends(require("treasury:read"))])
def hedge(p: HedgeRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return voyage.hedge_overlay(db, p.usd_cost, p.months, p.hedge_ratio_pct, p.inr_rate_pct, p.usd_rate_pct)
    except ValueError as exc:
        raise _bad(exc)


@router.get("/voyage/modal", dependencies=[Depends(require("recommend:read"))])
def modal(plant: str, origin_country: str, vessel_class: str = "Panamax", rail_inr_per_tkm: float = Query(1.4, gt=0, le=10),
          handling_usd: float = Query(4.0, ge=0, le=50), db: Session = Depends(get_db)) -> dict:
    try:
        return voyage.modal_compare(db, plant, origin_country, vessel_class, None, rail_inr_per_tkm, handling_usd)
    except ValueError as exc:
        raise _bad(exc)


@router.get("/voyage/plants", dependencies=[Depends(require("recommend:read"))])
def plants() -> dict:
    return {"plants": voyage.PLANTS, "origins": DEST_ORIGINS, "vessel_classes": list(voyage.REPRESENTATIVE_DWT)}


# ------------------------------------------------------------------ ledger
class LedgerIn(BaseModel):
    fixture_date: date
    vessel_name: str = Field(min_length=2, max_length=120)
    origin_country: str
    destination_port: str
    cargo_tonnes: float = Field(gt=0, le=500000)
    charter_type: str = Field(pattern="^(spot|time_charter|coa)$")
    rate_usd_per_tonne: float | None = Field(None, ge=0, le=500)
    notes: str | None = Field(None, max_length=500)


def _entry_out(e: LedgerEntry) -> dict:
    return {"id": e.id, "fixture_date": str(e.fixture_date), "vessel_name": e.vessel_name, "origin_country": e.origin_country, "destination_port": e.destination_port,
            "cargo_tonnes": float(e.cargo_tonnes), "charter_type": e.charter_type, "rate_usd_per_tonne": float(e.rate_usd_per_tonne) if e.rate_usd_per_tonne is not None else None,
            "notes": e.notes, "is_sample": e.is_sample, "created_at": str(e.created_at), "hash": e.entry_hash, "prev_hash": e.prev_hash}


def _ledger_query(db: Session, user: User):
    q = db.query(LedgerEntry)
    if not has(user, "ledger:read_all"):
        q = q.filter(LedgerEntry.created_by == user.id)  # row-level: own entries only
    return q


@router.get("/ledger")
def ledger_list(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    if not (has(user, "ledger:read_all") or has(user, "ledger:read_own")):
        raise HTTPException(status_code=403, detail=f"Your role ({role_of(user)['label']}) cannot access the fixture ledger.")
    entries = _ledger_query(db, user).order_by(LedgerEntry.id.desc()).all()
    chain = ledger.verify_chain(db)
    if not has(user, "ledger:read_all"):
        own_ids = {e.id for e in entries}
        chain = {**chain, "entries": len(entries), "head_hash": None,
                 "first_broken_id": chain["first_broken_id"] if chain["first_broken_id"] in own_ids else None,
                 "reason": chain["reason"] if chain["first_broken_id"] in own_ids else ("The shared chain has a break outside your entries." if not chain["valid"] else None)}
    return {"entries": [_entry_out(e) for e in entries], "chain": chain, "scope": "all entries" if has(user, "ledger:read_all") else "only entries you created"}


@router.post("/ledger", status_code=201, dependencies=[Depends(require("ledger:write"))])
def ledger_add(p: LedgerIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return _entry_out(ledger.add_entry(db, {**p.model_dump(), "is_sample": False}, user.id))


@router.post("/ledger/sample", dependencies=[Depends(require("ledger:write"))])
def ledger_sample(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    if db.query(LedgerEntry).filter(LedgerEntry.is_sample.is_(True), LedgerEntry.created_by == user.id).count():
        raise HTTPException(status_code=409, detail="You already loaded the sample entries")
    return {"added": ledger.load_sample(db, user.id)}


@router.get("/ledger/benchmark")
def ledger_benchmark(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    if not (has(user, "ledger:read_all") or has(user, "ledger:read_own")):
        raise HTTPException(status_code=403, detail=f"Your role ({role_of(user)['label']}) cannot access the fixture ledger.")
    allowed_ids = {e.id for e in _ledger_query(db, user).all()}
    rows = [r for r in ledger.benchmark(db) if r["id"] in allowed_ids]
    timed = [r["timing"]["missed_saving_pct"] for r in rows if r.get("timing")]
    return {"rows": rows, "summary": {"fixtures": len(rows), "avg_missed_saving_pct": round(sum(timed) / len(timed), 1) if timed else None},
            "method": "Timing: the real Panamax index (BPI) on the fixture date against its trailing 90 days and the cheapest day within 30 days either side. 'Missed saving' assumes the rate moves in proportion to the index, which is a simplification. Rate check: your rate against the platform's illustrative rate for the route."}


# ------------------------------------------------------------------ monitoring
@router.get("/monitor/{index_name}", dependencies=[Depends(require("monitor:read"))])
def monitor_status(index_name: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    try:
        name = index_name.upper()
        report = cached(f"drift:{name}:{data_version(db, name)}", 3600, lambda: monitor.drift_report(db, name))
        return {**report, "history": monitor.history(db, name)}
    except ValueError as exc:
        raise _bad(exc)


@router.post("/monitor/{index_name}/retrain", dependencies=[Depends(require("monitor:retrain"))])
def monitor_retrain(index_name: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    try:
        run = monitor.retrain(db, index_name.upper(), "manual")
    except ValueError as exc:
        raise _bad(exc)
    return {"run_id": run.id, "holdout_mape": float(run.holdout_mape) if run.holdout_mape is not None else None, "train_end": str(run.train_end)}


# ------------------------------------------------------------------ alerts
class RuleIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    kind: str
    param_a: str | None = None
    param_b: str | None = None
    threshold: float = 0
    webhook_url: str | None = Field(None, max_length=300)


def _rule_out(r: AlertRule) -> dict:
    return {"id": r.id, "name": r.name, "kind": r.kind, "param_a": r.param_a, "param_b": r.param_b, "threshold": float(r.threshold), "webhook_url": r.webhook_url,
            "active": r.active, "last_fired_at": str(r.last_fired_at) if r.last_fired_at else None}


@router.get("/alerts", dependencies=[Depends(require("alerts:manage"))])
def alerts_list(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    rules = db.query(AlertRule).filter(AlertRule.user_id == user.id).order_by(AlertRule.id.desc()).all()
    events = db.query(AlertEvent).filter(AlertEvent.user_id == user.id).order_by(AlertEvent.id.desc()).limit(50).all()
    return {"kinds": alert_service.KINDS, "rules": [_rule_out(r) for r in rules],
            "events": [{"id": e.id, "rule_id": e.rule_id, "fired_at": str(e.fired_at), "message": e.message, "delivery": e.delivery, "is_read": e.is_read} for e in events],
            "unread": sum(1 for e in events if not e.is_read),
            "channels": {"in_app": True, "webhook": True, "sms_whatsapp": "needs a messaging provider account (not configured)"}}


@router.post("/alerts", dependencies=[Depends(require("alerts:manage"))], status_code=201)
def alerts_create(p: RuleIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    if p.kind not in alert_service.KINDS:
        raise HTTPException(status_code=422, detail=f"kind must be one of {list(alert_service.KINDS)}")
    scope = port_scope(user)
    if scope is not None:
        if p.kind not in PORT_ALERT_KINDS:
            raise HTTPException(status_code=403, detail=f"Your role ({role_of(user)['label']}) can only create port alerts: {', '.join(sorted(PORT_ALERT_KINDS))}.")
        port_param = p.param_b if p.kind == "route_risk" else p.param_a
        if port_param not in scope:
            raise HTTPException(status_code=403, detail=f"{port_param} is outside the ports assigned to your account.")
    if p.webhook_url:
        try:
            alert_service.validate_webhook_url(p.webhook_url)
        except ValueError as exc:
            raise _bad(exc)
    if db.query(AlertRule).filter(AlertRule.user_id == user.id).count() >= 25:
        raise HTTPException(status_code=422, detail="Rule limit reached (25)")
    r = AlertRule(user_id=user.id, **p.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return _rule_out(r)


@router.delete("/alerts/{rule_id}", dependencies=[Depends(require("alerts:manage"))], status_code=204)
def alerts_delete(rule_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    r = db.query(AlertRule).filter(AlertRule.id == rule_id, AlertRule.user_id == user.id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.query(AlertEvent).filter(AlertEvent.rule_id == r.id).delete()
    db.delete(r)
    db.commit()


@router.post("/alerts/check", dependencies=[Depends(require("alerts:manage"))])
def alerts_check(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    fired = alert_service.evaluate(db, user.id)
    return {"fired": len(fired), "messages": [e.message for e in fired]}


@router.post("/alerts/read", dependencies=[Depends(require("alerts:manage"))])
def alerts_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    n = db.query(AlertEvent).filter(AlertEvent.user_id == user.id, AlertEvent.is_read.is_(False)).update({"is_read": True})
    db.commit()
    return {"marked": n}


# ------------------------------------------------------------------ explorer and briefing
@router.get("/data/series", dependencies=[Depends(require("market:read"))])
def data_series(db: Session = Depends(get_db)) -> list[dict]:
    return explorer.list_series(db)


@router.get("/data/query", dependencies=[Depends(require("market:read"))])
def data_query(index_name: str, start: date | None = None, end: date | None = None, min_value: float | None = None, max_value: float | None = None,
               limit: int = Query(500, ge=1, le=5000), db: Session = Depends(get_db)) -> dict:
    return explorer.query(db, index_name.upper(), start, end, min_value, max_value, limit)


@router.get("/data/export.csv", dependencies=[Depends(require("market:read"))])
def data_export(index_name: str, start: date | None = None, end: date | None = None, db: Session = Depends(get_db)) -> StreamingResponse:
    res = explorer.query(db, index_name.upper(), start, end, None, None, 50000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "value", "unit"])
    for r in reversed(res["rows"]):
        w.writerow([r["date"], r["value"], r["unit"]])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{index_name.upper()}.csv"'})


@router.get("/data/search", dependencies=[Depends(require("market:read"))])
def data_search(q: str = Query(min_length=2, max_length=60), db: Session = Depends(get_db)) -> dict:
    return explorer.search(db, q)


@router.get("/briefing", dependencies=[Depends(require("assistant:use"))])
def get_briefing(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    scope_key = "|".join(sorted(has_perms(user)))
    return cached(f"briefing:{data_version(db, 'BPI')}:{date.today()}:{scope_key}:{','.join(port_scope(user) or ['*'])}", 1800, lambda: briefing.build(db, user))
