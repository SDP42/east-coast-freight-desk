from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require
from app.core.permissions import port_scope
from app.db.session import get_db
from app.models import User
from app.services.portmap import build_map_overview

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(require("ports:read"))) -> dict:
    """Ports (real), sea lanes and simulated vessels for the map view."""
    data = build_map_overview(db, port_scope(user))
    # Real availability: ships from the user's uploaded broker lists, pinned at the origin they are open in (only for roles that may see tonnage).
    from app.core.permissions import has
    from app.models import OpenTonnage
    from app.services.tonnage import origin_of

    counts: dict[str, dict] = {}
    if has(user, "recommend:read"):
        for t in db.query(OpenTonnage).all():
            o = origin_of(t.open_port)
            if o:
                c = counts.setdefault(o, {"ships": 0, "dwt": 0, "sample": True, "names": []})
                c["ships"] += 1
                c["dwt"] += t.dwt
                c["sample"] = c["sample"] and bool(t.is_sample)
                if len(c["names"]) < 6:
                    c["names"].append(f"{t.vessel_name} ({t.dwt:,} t, open {t.open_date:%d %b})")
    data["open_tonnage"] = counts
    return data
