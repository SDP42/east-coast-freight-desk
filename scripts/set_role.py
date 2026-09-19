"""Assign a role (and optionally ports) to an existing account.

Usage: backend/.venv/bin/python scripts/set_role.py you@example.com admin
       backend/.venv/bin/python scripts/set_role.py officer@example.com port_ops Haldia Paradip"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.permissions import ROLES  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[2] not in ROLES:
        raise SystemExit(f"Usage: set_role.py EMAIL ROLE [PORT ...]   roles: {', '.join(ROLES)}")
    db = SessionLocal()
    u = db.query(User).filter(User.email == sys.argv[1]).first()
    if not u:
        raise SystemExit("No such account")
    u.role = sys.argv[2]
    u.assigned_ports = json.dumps(sys.argv[3:]) if len(sys.argv) > 3 else None
    db.commit()
    print(f"{u.email} is now {u.role}" + (f" for {sys.argv[3:]}" if len(sys.argv) > 3 else ""))


if __name__ == "__main__":
    main()
