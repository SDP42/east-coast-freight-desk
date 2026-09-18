"""Ingest S&P 500 and the Trade-Weighted US Dollar Index (DTWEXBGS) from FRED
(Federal Reserve, free, no API key) into `freight_rates` (shared market-series
table). Directly motivated by Kim, Kim & Choi (2025, PLOS ONE), who found via
SHAP — across 10 different ML models — that the S&P 500 is the single
strongest predictor of BDI, ahead of any shipping-specific variable, with the
US Dollar Index second. Not a guess: a literature-directed feature choice.

Run from the backend venv: ../backend/.venv/bin/python3 ingest_macro_indicators.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import FreightRate  # noqa: E402

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
SOURCE_CITATION = "FRED (Federal Reserve Bank of St. Louis)"

FILES = {
    "SP500": RAW_DIR / "FRED_SP500.csv",
    "DXY": RAW_DIR / "FRED_DTWEXBGS.csv",
}


def main() -> None:
    db = SessionLocal()
    existing = db.query(FreightRate).filter(FreightRate.source == SOURCE_CITATION).count()
    if existing:
        print(f"Already ingested {existing} rows from FRED — skipping.")
        db.close()
        return

    rows: list[FreightRate] = []
    for series_name, path in FILES.items():
        if not path.exists():
            print(f"Skipping {series_name}: {path} not found.")
            continue
        df = pd.read_csv(path)
        value_col = df.columns[1]
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        df = df.dropna(subset=[value_col])

        for _, row in df.iterrows():
            rows.append(
                FreightRate(
                    rate_date=pd.to_datetime(row["observation_date"]).date(),
                    index_name=series_name,
                    value=float(row[value_col]),
                    unit="index_points" if series_name == "DXY" else "usd",
                    source=SOURCE_CITATION,
                )
            )
        print(f"{series_name}: {len(df)} rows ({df['observation_date'].min()} to {df['observation_date'].max()})")

    db.bulk_save_objects(rows)
    db.commit()
    print(f"Ingested {len(rows)} macro indicator observations total.")
    db.close()


if __name__ == "__main__":
    main()
