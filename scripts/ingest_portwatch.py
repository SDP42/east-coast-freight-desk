"""Ingest IMF PortWatch daily dry-bulk port calls (East Coast India) and chokepoint transits.

Source files come from the PortWatch public ArcGIS service (see data/raw/candidates/MANIFEST.md).
Tonnes are AIS-derived estimates. Licence terms should be confirmed before redistribution.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import ChokepointTransit, PortActivity  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "candidates"
PORTS_FILE = RAW / "imf_portwatch_daily_ec_india_ports.csv"
CHOKE_FILE = RAW / "imf_portwatch_daily_chokepoints.csv"
NAME_MAP = {"Visakhapatnam": "Visakhapatnam", "Paradip": "Paradip", "Haldia": "Haldia", "Dhamra Port": "Dhamra", "Gopalpur": "Gopalpur"}


def main() -> None:
    if not PORTS_FILE.exists() or not CHOKE_FILE.exists():
        print("PortWatch files not found in data/raw/candidates - skipping.")
        return
    db = SessionLocal()
    db.query(PortActivity).delete()
    db.query(ChokepointTransit).delete()

    p = pd.read_csv(PORTS_FILE, parse_dates=["date"])
    p = p[p.portname.isin(NAME_MAP)]
    db.bulk_save_objects([
        PortActivity(port_name=NAME_MAP[r.portname], activity_date=r.date.date(), dry_bulk_calls=int(r.portcalls_dry_bulk),
                     dry_bulk_import_t=int(r.import_dry_bulk), dry_bulk_export_t=int(r.export_dry_bulk))
        for r in p.itertuples()
    ])

    c = pd.read_csv(CHOKE_FILE, parse_dates=["date"])
    db.bulk_save_objects([
        ChokepointTransit(chokepoint=r.portname, transit_date=r.date.date(), dry_bulk_transits=int(r.n_dry_bulk),
                          dry_bulk_capacity_dwt=int(r.capacity_dry_bulk))
        for r in c.itertuples()
    ])
    db.commit()
    print(f"Ingested {len(p)} port-day rows and {len(c)} chokepoint-day rows.")
    db.close()


if __name__ == "__main__":
    main()
