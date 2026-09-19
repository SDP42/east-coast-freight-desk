"""Ingest the real daily Baltic Dry Index (2006-02-23 to 2026-02-20) into `freight_rates`.

Replaces the earlier BDI that was computed from sub-indices (0.4*CI+0.3*PI+0.3*SI),
which ran about 15% above the published BDI. Source is a GitHub mirror of an
Investing.com export; internal research use only, the raw file stays gitignored.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import FreightRate  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "candidates" / "gh_lumaita_bdi_daily_raw.csv"
SOURCE = "Investing.com daily BDI via GitHub mirror LuMaIta/shipping-market-tracker (internal research use)"


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"Missing {RAW}")
    df = pd.read_csv(RAW, encoding="utf-8-sig", thousands=",")
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
    df = df.dropna(subset=["Price"]).drop_duplicates("Date").sort_values("Date")

    db = SessionLocal()
    removed = db.query(FreightRate).filter(FreightRate.index_name == "BDI").delete()
    db.bulk_save_objects([
        FreightRate(rate_date=r.Date.date(), index_name="BDI", value=float(r.Price), unit="points", source=SOURCE)
        for r in df.itertuples()
    ])
    db.commit()
    print(f"Replaced {removed} old BDI rows with {len(df)} real rows ({df.Date.min().date()} to {df.Date.max().date()}).")
    db.close()


if __name__ == "__main__":
    main()
