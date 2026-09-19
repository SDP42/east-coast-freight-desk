"""Run the full data ingestion pipeline in dependency order.

Run from the backend venv: ../backend/.venv/bin/python3 run_all.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "seed_ports.py",
    "seed_port_coordinates.py",
    "seed_routes.py",
    "generate_synthetic_vessels.py",
    "seed_disruption_events.py",
    "ingest_macro_indicators.py",
    "ingest_latest.py",
    "ingest_usda_ocean.py",
    "ingest_port_turnaround.py",
    "ingest_cyclones.py",
]


def main() -> None:
    here = Path(__file__).resolve().parent
    for script in SCRIPTS:
        print(f"\n=== {script} ===")
        result = subprocess.run([sys.executable, str(here / script)])
        if result.returncode != 0:
            raise SystemExit(f"{script} failed (exit {result.returncode})")


if __name__ == "__main__":
    main()
