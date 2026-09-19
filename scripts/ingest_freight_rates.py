"""Ingest the real Mendeley Baltic Dry sub-index dataset (DOI 10.17632/t76ckh2ygg.1,
CC BY 4.0) into the `freight_rates` table.

Source file: data/raw/edited_BDI_data1.xls, sheet "MASTER EXCEL SHEET BDI ",
1,749 daily rows from 1 Aug 2012 to 31 Jul 2019. Columns HSI/SI/PI/CI map to
our index_name values BHSI/BSI/BPI/BCI (Handysize/Supramax/Panamax/Capesize).

Run from the backend venv: ../backend/.venv/bin/python3 ingest_freight_rates.py
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import FreightRate  # noqa: E402

RAW_FILE = Path(__file__).resolve().parents[1] / "data" / "raw" / "edited_BDI_data1.xls"
SHEET_NAME = "MASTER EXCEL SHEET BDI "
SOURCE_CITATION = "Mendeley Data, DOI 10.17632/t76ckh2ygg.1 (CC BY 4.0)"

COLUMN_TO_INDEX = {
    "HSI": "BHSI",
    "SI": "BSI",
    "PI": "BPI",
    "CI": "BCI",
}


def main() -> None:
    if not RAW_FILE.exists():
        raise SystemExit(f"Raw dataset not found at {RAW_FILE} — fetch it first.")

    df = pd.read_excel(RAW_FILE, sheet_name=SHEET_NAME)
    df["Date"] = pd.to_datetime(df["Date"], format="%b %d, %Y")

    db = SessionLocal()
    existing = db.query(FreightRate).filter(FreightRate.source == SOURCE_CITATION).count()
    if existing:
        print(f"Already ingested {existing} rows from this source — skipping (delete them first to re-run).")
        db.close()
        return

    rows: list[FreightRate] = []
    for _, row in df.iterrows():
        rate_date = row["Date"].date()
        for column, index_name in COLUMN_TO_INDEX.items():
            value = row[column]
            if pd.isna(value):
                continue
            rows.append(
                FreightRate(
                    rate_date=rate_date,
                    index_name=index_name,
                    value=float(value),
                    unit="points",
                    source=SOURCE_CITATION,
                )
            )

    db.bulk_save_objects(rows)
    db.commit()
    print(f"Ingested {len(rows)} freight rate observations "
          f"({df['Date'].min().date()} to {df['Date'].max().date()}, "
          f"{len(COLUMN_TO_INDEX)} sub-indices).")
    db.close()


if __name__ == "__main__":
    started = datetime.now()
    main()
    print(f"Done in {(datetime.now() - started).total_seconds():.1f}s")
