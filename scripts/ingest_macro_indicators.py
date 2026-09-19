"""Ingest macro/market series from FRED (Federal Reserve, free, no API key) into
`freight_rates` (the shared market-series table).

- DXY (the Fed's broad dollar index): the dollar
  index second.
- INR, AUD, ZAR: regional FX series for the region boards in the UI — INR/USD
  is the destination-side rate (freight is USD-quoted, Indian budgets are INR),
  AUD and ZAR proxy the Australian and Southern African/Mozambique origin
  economies.

Each series is ingested independently and skipped if already present.

Run from the backend venv: ../backend/.venv/bin/python3 ingest_macro_indicators.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import _download  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import FreightRate  # noqa: E402

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
SOURCE_CITATION = "FRED (Federal Reserve Bank of St. Louis)"

# series name -> (file, unit)
FILES = {
    "DXY": (RAW_DIR / "FRED_DTWEXBGS.csv", "index_points"),
    "INR": (RAW_DIR / "FRED_DEXINUS.csv", "inr_per_usd"),
    "AUD": (RAW_DIR / "FRED_DEXUSAL.csv", "usd_per_aud"),
    "ZAR": (RAW_DIR / "FRED_DEXSFUS.csv", "zar_per_usd"),
}


FRED_ID = {"DXY": "DTWEXBGS", "INR": "DEXINUS", "AUD": "DEXUSAL", "ZAR": "DEXSFUS"}


def main() -> None:
    db = SessionLocal()
    total = 0
    for series_name, (path, unit) in FILES.items():
        if db.query(FreightRate).filter(FreightRate.index_name == series_name).count():
            print(f"{series_name}: already ingested — skipping.")
            continue
        if not _download.fred(FRED_ID[series_name], path):
            print(f"{series_name}: {path.name} not available — skipping.")
            continue

        df = pd.read_csv(path)
        value_col = df.columns[1]
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        df = df.dropna(subset=[value_col])

        rows = [
            FreightRate(
                rate_date=pd.to_datetime(d).date(), index_name=series_name,
                value=float(v), unit=unit, source=SOURCE_CITATION,
            )
            for d, v in zip(df["observation_date"], df[value_col])
        ]
        db.bulk_save_objects(rows)
        db.commit()
        total += len(rows)
        print(f"{series_name}: {len(rows)} rows ({df['observation_date'].min()} to {df['observation_date'].max()})")

    print(f"Ingested {total} new macro observations.")
    db.close()


if __name__ == "__main__":
    main()
