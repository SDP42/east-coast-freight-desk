"""Strip demo and sample data before a real deployment. Dry run by default; pass --apply to delete.

Removes: the demo accounts (is_demo) and their audit-log rows, the sample ledger entries and the sample tonnage list, the
synthetic vessels used only by the simulated port-map layer, and the demo users' alert rules. Real users, real ledger entries
and real uploaded tonnage are kept. Run against the deployment database (DATABASE_URL), never against one you still demo from.
Also set ALLOW_DEMO_LOGIN=false and leave SHOW_SIMULATED_FEEDS and LIVE_SHIP_FEED unset.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import AlertEvent, AlertRule, AuditLog, LedgerEntry, OpenTonnage, User, Vessel  # noqa: E402


def main() -> None:
    apply = "--apply" in sys.argv
    db = SessionLocal()
    demo_ids = [u.id for u in db.query(User).filter(User.is_demo.is_(True)).all()]
    plan = {
        "demo users": db.query(User).filter(User.is_demo.is_(True)).count(),
        "audit rows of demo users": db.query(AuditLog).filter(AuditLog.user_id.in_(demo_ids)).count() if demo_ids else 0,
        "sample ledger entries": db.query(LedgerEntry).filter(LedgerEntry.is_sample.is_(True)).count(),
        "sample tonnage": db.query(OpenTonnage).filter(OpenTonnage.is_sample.is_(True)).count(),
        "synthetic vessels": db.query(Vessel).filter(Vessel.is_synthetic.is_(True)).count(),
        "alert rules of demo users": db.query(AlertRule).filter(AlertRule.user_id.in_(demo_ids)).count() if demo_ids else 0,
    }
    for k, v in plan.items():
        print(f"{'would delete' if not apply else 'deleting':13s} {v:5d}  {k}")
    if not apply:
        print("\nDry run. Nothing changed. Re-run with --apply on the deployment database.")
        return
    if demo_ids:
        rule_ids = [r.id for r in db.query(AlertRule).filter(AlertRule.user_id.in_(demo_ids)).all()]
        if rule_ids:
            db.query(AlertEvent).filter(AlertEvent.rule_id.in_(rule_ids)).delete(synchronize_session=False)
        db.query(AlertRule).filter(AlertRule.user_id.in_(demo_ids)).delete(synchronize_session=False)
        db.query(AuditLog).filter(AuditLog.user_id.in_(demo_ids)).delete(synchronize_session=False)
    # A sample ledger entry sits inside the hash chain; deleting from the middle would break it, so clear all entries only if every one is a sample.
    if db.query(LedgerEntry).filter(LedgerEntry.is_sample.is_(False)).count() == 0:
        db.query(LedgerEntry).delete()
    elif plan["sample ledger entries"]:
        print("NOTE: real ledger entries exist alongside samples; the samples are left so the hash chain stays valid. Rebuild the chain manually if needed.")
    db.query(OpenTonnage).filter(OpenTonnage.is_sample.is_(True)).delete(synchronize_session=False)
    db.query(Vessel).filter(Vessel.is_synthetic.is_(True)).delete(synchronize_session=False)
    if demo_ids:
        db.query(User).filter(User.id.in_(demo_ids)).delete(synchronize_session=False)
    db.commit()
    print("Done.")


if __name__ == "__main__":
    main()
