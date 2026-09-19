"""Set ports.avg_turnaround_hours from the Ministry of Ports 'Update on the Indian Ports Sector'
(FY2024-25 provisional average turn-round time, parsed from the PDF and spot-checked).
Only major ports are covered; Dhamra, Gopalpur and Gangavaram (non-major) stay empty.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Port  # noqa: E402

FILE = Path(__file__).resolve().parents[1] / "data" / "seed" / "ministry_of_ports_avg_turnaround_hours.csv"  # small government table, kept in the repo
PORT_MAP = {"Paradip Port Authority": "Paradip", "Visakhapatnam Port Authority": "Visakhapatnam", "SMP Haldia DC": "Haldia"}
SOURCE = "Ministry of Ports, Shipping & Waterways, Update on the Indian Ports Sector (to 31.03.2025), FY2024-25P avg turn-round time"


def main() -> None:
    if not FILE.exists():
        print("Turnaround file not found - skipping.")
        return
    df = pd.read_csv(FILE).set_index("port")
    db = SessionLocal()
    for src, name in PORT_MAP.items():
        port = db.query(Port).filter(Port.name == name).one_or_none()
        if port is None:
            continue
        port.avg_turnaround_hours = float(df.loc[src, "2024-25P"])
        if SOURCE not in (port.source or ""):
            port.source = f"{port.source or ''} | {SOURCE}".strip(" |")
        print(f"{name}: {port.avg_turnaround_hours} h")
    db.commit()
    db.close()


if __name__ == "__main__":
    main()
