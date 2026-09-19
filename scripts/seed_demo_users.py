"""Create the demo accounts (one per role) with sample fixtures, so every access level can be shown.

Demo accounts are flagged `is_demo`, get random unusable passwords, and sign in through the one-click demo
login (ALLOW_DEMO_LOGIN). Re-running is safe: existing demo accounts are updated, not duplicated."""

import json
import os
import secrets
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import LedgerEntry, User  # noqa: E402
from app.services import ledger  # noqa: E402

# Optional shared password so the demo accounts can also sign in by typing it. Unset: one-click demo sign-in only.
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD")

DEMO = [
    ("admin@demo.example.com", "Asha Verma", "admin", None, "finance_head"),
    ("finance@demo.example.com", "Rohan Iyer", "finance_head", None, "finance_head"),
    ("procurement@demo.example.com", "Priya Nair", "procurement_manager", None, "procurement_manager"),
    ("analyst@demo.example.com", "Karan Mehta", "chartering_analyst", None, "chartering_analyst"),
    ("haldia.ops@demo.example.com", "Sourav Das", "port_ops", ["Haldia"], "port_ops"),
    ("paradip.ops@demo.example.com", "Meera Patra", "port_ops", ["Paradip"], "port_ops"),
]
# Sample fixtures (invented, marked as samples) given to different owners so row-level scoping is visible.
SAMPLES = [
    ("finance@demo.example.com", date(2014, 3, 10), "MV Sample Harmony", "Australia", "Paradip", 75000, "coa", 14.2),
    ("procurement@demo.example.com", date(2015, 11, 16), "MV Sample Dawn", "Australia", "Haldia", 33000, "spot", 17.8),
    ("procurement@demo.example.com", date(2016, 2, 8), "MV Sample Meridian", "Mozambique", "Visakhapatnam", 70000, "spot", 22.5),
    ("analyst@demo.example.com", date(2017, 6, 12), "MV Sample Tern", "Russia", "Paradip", 65000, "spot", 41.0),
    ("analyst@demo.example.com", date(2018, 9, 10), "MV Sample Crest", "United States", "Gangavaram", 80000, "spot", 36.5),
    ("finance@demo.example.com", date(2019, 3, 4), "MV Sample Lantern", "Indonesia", "Dhamra", 55000, "coa", 6.9),
]


def main() -> None:
    db = SessionLocal()
    ids: dict[str, int] = {}
    for email, name, role, ports, persona in DEMO:
        u = db.query(User).filter(User.email == email).first()
        if u is None:
            u = User(email=email, hashed_password=hash_password(DEMO_PASSWORD or secrets.token_urlsafe(24)))
            db.add(u)
        elif DEMO_PASSWORD:
            u.hashed_password = hash_password(DEMO_PASSWORD)
        u.full_name, u.role, u.persona, u.is_demo, u.is_active = name, role, persona, True, True
        u.assigned_ports = json.dumps(ports) if ports else None
        db.flush()
        ids[email] = u.id
    db.commit()
    if db.query(LedgerEntry).filter(LedgerEntry.is_sample.is_(True)).count() == 0:
        for owner, d, vessel, origin, port, cargo, ctype, rate in SAMPLES:
            ledger.add_entry(db, dict(fixture_date=d, vessel_name=vessel, origin_country=origin, destination_port=port, cargo_tonnes=cargo, charter_type=ctype,
                                      rate_usd_per_tonne=rate, notes="Illustrative sample entry, not a real fixture", is_sample=True), ids[owner])
    print(f"Demo accounts ready: {', '.join(e for e, *_ in DEMO)}")
    db.close()


if __name__ == "__main__":
    main()
