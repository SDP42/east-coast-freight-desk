"""Ingest World Bank Commodity Markets ("Pink Sheet") historical monthly coal
prices into `freight_rates` (shared market-series table) — demand-side/
commodity signal for the forecasting models. Kim et al. (2025, PLOS ONE, cited
in our research compendium) found coal/iron-ore prices among the strongest BDI
predictors via SHAP, which is why this matters for Section 5/6.

Source: World Bank Commodity Markets historical monthly data (public), sheet
"Monthly Prices". Columns used: "Coal, Australian", "Coal, South African **".

Run from the backend venv: ../backend/.venv/bin/python3 ingest_commodity_prices.py
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import FreightRate  # noqa: E402

RAW_FILE = Path(__file__).resolve().parents[1] / "data" / "raw" / "CMO-Historical-Data-Monthly.xlsx"
SOURCE_CITATION = "World Bank Commodity Markets (Pink Sheet), Monthly Prices"

COLUMN_TO_SERIES = {
    "Coal, Australian": "COAL_AUS",
    "Coal, South African **": "COAL_ZA",
}


def parse_period(value: str) -> date:
    # Format: "2024M10" -> first of that month
    year, month = value.split("M")
    return date(int(year), int(month), 1)


def main() -> None:
    if not RAW_FILE.exists():
        raise SystemExit(f"Raw dataset not found at {RAW_FILE} — fetch it first.")

    df = pd.read_excel(RAW_FILE, sheet_name="Monthly Prices", skiprows=4)
    df = df.rename(columns={df.columns[0]: "period"})
    df = df[df["period"].astype(str).str.match(r"^\d{4}M\d{2}$", na=False)]

    db = SessionLocal()
    existing = db.query(FreightRate).filter(FreightRate.source == SOURCE_CITATION).count()
    if existing:
        print(f"Already ingested {existing} rows from this source — skipping.")
        db.close()
        return

    rows: list[FreightRate] = []
    for _, row in df.iterrows():
        rate_date = parse_period(str(row["period"]))
        for column, series_name in COLUMN_TO_SERIES.items():
            value = pd.to_numeric(row.get(column), errors="coerce")
            if pd.isna(value):
                continue
            rows.append(
                FreightRate(
                    rate_date=rate_date,
                    index_name=series_name,
                    value=float(value),
                    unit="usd_per_tonne",
                    source=SOURCE_CITATION,
                )
            )

    db.bulk_save_objects(rows)
    db.commit()
    print(f"Ingested {len(rows)} commodity price observations "
          f"({len(COLUMN_TO_SERIES)} series, {df['period'].min()} to {df['period'].max()}).")
    db.close()


if __name__ == "__main__":
    main()
