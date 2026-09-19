"""Configurable alerting (#27, partly #14). Rules are evaluated against the same engines the dashboard
uses; a fired rule creates an in-app event and, if a webhook URL is set, POSTs a JSON payload to it.
SMS and WhatsApp need a messaging provider account and are not configured."""

import ipaddress
import socket
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.models import AlertEvent, AlertRule, Port
from app.services import monitor, signals
from app.services.freight_data import load_series
from app.services.quick_forecast import quick_forecast
from app.services.risk import _congestion_score, compute_route_risk

KINDS = {
    "index_move_pct": "A series moved by at least this many percent in its latest day",
    "forecast_change_pct": "14-day forecast change reaches this percent (positive = rise, negative = fall, i.e. a buying window)",
    "port_congestion": "A port's congestion score reaches this level (0-10)",
    "route_risk": "A route's composite risk score reaches this level (0-10)",
    "model_drift": "The forecast model is flagged as drifting (threshold ignored)",
    "cyclone_probability": "Chance of a storm near a port in the next 30 days reaches this fraction (0-1)",
}


def validate_webhook_url(url: str) -> str:
    p = urlparse(url)
    if p.scheme != "https" or not p.hostname:
        raise ValueError("Webhook URL must be https")
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ValueError("Webhook host does not resolve") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("Webhook host must be a public address")
    return url


def _check(db: Session, r: AlertRule) -> str | None:
    t = float(r.threshold)
    if r.kind == "index_move_pct":
        s = load_series(db, r.param_a or "OCEAN_GULF_JAPAN")
        if len(s) < 2:
            return None
        ch = (float(s.iloc[-1]) / float(s.iloc[-2]) - 1) * 100
        return f"{r.param_a or 'OCEAN_GULF_JAPAN'} moved {ch:+.1f}% on {s.index[-1].date()}" if abs(ch) >= t else None
    if r.kind == "forecast_change_pct":
        f = quick_forecast(db, r.param_a or "OCEAN_GULF_JAPAN", int(r.param_b or 3))
        if f is None:
            return None
        hit = f.change_pct >= t if t >= 0 else f.change_pct <= t
        return (f"{f.index_name} forecast {f.change_pct:+.1f}% over {f.horizon} step(s) ({f.last_value:,.0f} to {f.forecast_end:,.0f})"
                + (" - a possible buying window" if f.change_pct < 0 else "")) if hit else None
    if r.kind == "port_congestion":
        port = db.query(Port).filter(Port.name == r.param_a).first()
        if not port:
            return None
        sc, detail = _congestion_score(port, db)
        return f"{port.name} congestion {sc:.1f}/10: {detail}" if sc >= t else None
    if r.kind == "route_risk":
        port = db.query(Port).filter(Port.name == r.param_b).first()
        if not port:
            return None
        rr = compute_route_risk(db, r.param_a or "Australia", port)
        return f"{r.param_a} to {port.name} risk {rr.composite_score:.1f}/10 ({rr.risk_label})" if rr.composite_score >= t else None
    if r.kind == "model_drift":
        rep = monitor.drift_report(db, r.param_a or "BRENT")
        return f"{rep['index_name']} model drift: error ratio {rep['error_ratio']}, return PSI {rep['return_psi']}" if rep["status"] == "drift" else None
    if r.kind == "cyclone_probability":
        res = signals.cyclone_eta_risk(db, r.param_a or "Paradip", date.today(), date.today() + timedelta(days=30))
        return f"{res['port']}: {res['probability_storm_in_window']:.0%} chance of a storm in the next 30 days" if res["probability_storm_in_window"] >= t else None
    return None


def _deliver(r: AlertRule, message: str) -> str:
    if not r.webhook_url:
        return "in_app"
    try:
        validate_webhook_url(r.webhook_url)
        resp = httpx.post(r.webhook_url, json={"rule": r.name, "message": message, "fired_at": datetime.utcnow().isoformat() + "Z"}, timeout=4.0, follow_redirects=False)
        return f"in_app + webhook {resp.status_code}"
    except Exception as exc:  # delivery must never break evaluation
        return f"in_app; webhook failed ({type(exc).__name__})"


def evaluate(db: Session, user_id: int | None = None) -> list[AlertEvent]:
    q = db.query(AlertRule).filter(AlertRule.active.is_(True))
    if user_id is not None:
        q = q.filter(AlertRule.user_id == user_id)
    fired: list[AlertEvent] = []
    for r in q.all():
        try:
            msg = _check(db, r)
        except Exception:
            continue
        if not msg:
            continue
        recent = db.query(AlertEvent).filter(AlertEvent.rule_id == r.id, AlertEvent.message == msg, AlertEvent.fired_at >= datetime.utcnow() - timedelta(hours=24)).first()
        if recent:
            continue
        ev = AlertEvent(rule_id=r.id, user_id=r.user_id, message=msg, delivery=_deliver(r, msg))
        r.last_fired_at = datetime.utcnow()
        db.add(ev)
        fired.append(ev)
    db.commit()
    return fired
