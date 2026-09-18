"""User personas — stored in the existing `users.role` column. A persona shapes
the default experience (which tools are surfaced first, greeting, quick
actions); it is not a permission boundary except for `admin`, which cannot be
chosen at self-registration."""

PERSONAS = {
    "procurement_manager": {
        "label": "Procurement Manager",
        "description": "Decides when and how to buy freight: which origin, which vessel, spot or COA.",
        "focus": ["recommendation", "financial", "scenario"],
        "self_register": True,
    },
    "chartering_analyst": {
        "label": "Chartering Analyst",
        "description": "Watches the freight market and forecasts, and builds the case for a fixture.",
        "focus": ["markets", "forecast", "recommendation"],
        "self_register": True,
    },
    "port_ops": {
        "label": "Port & Logistics Officer",
        "description": "Manages berth fit, congestion and disruption risk at the East Coast ports.",
        "focus": ["ports", "risk", "map"],
        "self_register": True,
    },
    "finance_head": {
        "label": "Finance & Treasury",
        "description": "Owns freight cost exposure, hedging, and the savings case.",
        "focus": ["financial", "markets", "scenario"],
        "self_register": True,
    },
    "admin": {
        "label": "Administrator",
        "description": "Full access. Assigned by an existing administrator, not at sign-up.",
        "focus": ["markets", "forecast", "recommendation", "ports", "risk", "financial", "scenario"],
        "self_register": False,
    },
}

DEFAULT_PERSONA = "chartering_analyst"
SELF_REGISTER_PERSONAS = [k for k, v in PERSONAS.items() if v["self_register"]]
