"""Role-based access control. `role` (assigned by an administrator, never chosen at sign-up) decides what a
user may read; `persona` only shapes the interface. Permissions gate whole domains; `port_scoped` roles are
additionally restricted, at query level, to the ports assigned to their account."""

PERMISSION_LABELS = {
    "market:read": "Freight, coal, FX and equity series, forecasts, data explorer",
    "recommend:read": "Origin comparison, Pareto ranking, scenarios, carbon and rail-sea-rail",
    "financial:read": "COA vs spot, ROI, demurrage, ballast and idle-time",
    "treasury:read": "INR/USD hedging overlay",
    "ports:read": "Port constraints, berth fit, congestion, the port map and port signals",
    "risk:read": "Route risk scores and disruption events",
    "demand:read": "SAIL coal demand and import volumes",
    "ledger:read_own": "Fixture ledger: entries you created",
    "ledger:read_all": "Fixture ledger: every entry",
    "ledger:write": "Add fixtures to the ledger",
    "alerts:manage": "Create and read your own alert rules",
    "monitor:read": "Model drift monitor",
    "monitor:retrain": "Retrain forecast models",
    "assistant:use": "Ask the Freight Desk (answers are limited to what your role may see)",
    "admin:users": "Manage users, roles, port assignments and read the audit log",
}

_ALL = set(PERMISSION_LABELS)

ROLES = {
    "admin": {
        "label": "Administrator", "level": 5, "port_scoped": False, "permissions": _ALL,
        "summary": "Everything, including user management and the audit log.",
    },
    "finance_head": {
        "label": "Finance & Treasury", "level": 4, "port_scoped": False,
        "permissions": {"market:read", "recommend:read", "financial:read", "treasury:read", "ports:read", "risk:read", "demand:read",
                        "ledger:read_all", "ledger:write", "alerts:manage", "monitor:read", "assistant:use"},
        "summary": "All commercial and financial data, including hedging and every fixture; no user management.",
    },
    "procurement_manager": {
        "label": "Procurement Manager", "level": 3, "port_scoped": False,
        "permissions": {"market:read", "recommend:read", "financial:read", "ports:read", "risk:read", "demand:read",
                        "ledger:read_all", "ledger:write", "alerts:manage", "monitor:read", "assistant:use"},
        "summary": "Sourcing, freight, cost and every fixture; no hedging and no user management.",
    },
    "chartering_analyst": {
        "label": "Chartering Analyst", "level": 2, "port_scoped": False,
        "permissions": {"market:read", "recommend:read", "ports:read", "risk:read", "ledger:read_own", "ledger:write", "alerts:manage",
                        "monitor:read", "monitor:retrain", "assistant:use"},
        "summary": "Markets, forecasts and recommendations; only their own fixtures; no cost, hedging or volume data.",
    },
    "port_ops": {
        "label": "Port & Logistics Officer", "level": 1, "port_scoped": True,
        "permissions": {"ports:read", "risk:read", "alerts:manage", "assistant:use"},
        "summary": "Only the ports assigned to their account: berth fit, congestion, cyclone and slot signals, and risk into those ports.",
    },
    "viewer": {
        "label": "Viewer", "level": 0, "port_scoped": False,
        "permissions": {"market:read", "assistant:use"},
        "summary": "Public market data only. New accounts start here until an administrator assigns a role.",
    },
}

PORT_ALERT_KINDS = {"port_congestion", "route_risk", "cyclone_probability"}
DEFAULT_ROLE = "viewer"


def role_of(user) -> dict:
    return ROLES.get(getattr(user, "role", None) or DEFAULT_ROLE, ROLES[DEFAULT_ROLE])


def permissions_of(user) -> set[str]:
    return set(role_of(user)["permissions"])


def has(user, permission: str) -> bool:
    return permission in permissions_of(user)


def assigned_ports(user) -> list[str]:
    import json

    raw = getattr(user, "assigned_ports", None)
    try:
        return list(json.loads(raw)) if raw else []
    except (TypeError, ValueError):
        return []


def port_scope(user) -> list[str] | None:
    """None means every port; otherwise the only port names this user may see (possibly empty)."""
    return assigned_ports(user) if role_of(user)["port_scoped"] else None


def can_see_port(user, port_name: str) -> bool:
    scope = port_scope(user)
    return scope is None or port_name in scope
