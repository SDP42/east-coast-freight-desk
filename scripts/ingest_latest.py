"""Bring the public-domain market series up to date from FRED (St. Louis Fed), which serves US-government series with no key.

Only series that are US-government works are used, so no licence conditions apply:
  WPU30130101   US BLS Producer Price Index, deep-sea freight (monthly)         -> DEEPSEA_PPI
  WPU051        US BLS Producer Price Index, coal (monthly)                     -> COAL_PPI
  DCOILBRENTEU  US EIA Brent crude oil spot price, US$ per barrel (daily)       -> BRENT
Safe to re-run: only dates newer than the latest stored row are added.
"""

import io
import sys
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import func  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import FreightRate  # noqa: E402

SERIES = [
    ("WPU30130101", "DEEPSEA_PPI", "index_points", "US BLS PPI: deep-sea freight, via FRED"),
    ("WPU051", "COAL_PPI", "index_points", "US BLS PPI: coal, via FRED"),
    ("DCOILBRENTEU", "BRENT", "usd_per_barrel", "US EIA Brent crude spot price, via FRED"),
]


def fetch(series_id: str) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (freight-desk research prototype)"})
    df = pd.read_csv(io.StringIO(urllib.request.urlopen(req, timeout=60).read().decode()))
    df.columns = ["date", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna()


def main() -> None:
    db = SessionLocal()
    for fred_id, name, unit, source in SERIES:
        try:
            df = fetch(fred_id)
        except Exception as e:  # noqa: BLE001
            print(f"{name}: could not fetch {fred_id} ({e}); left unchanged")
            continue
        latest = db.query(func.max(FreightRate.rate_date)).filter(FreightRate.index_name == name).scalar()
        rows = [FreightRate(rate_date=date.fromisoformat(r.date), index_name=name, value=float(r.value), unit=unit, source=source)
                for r in df.itertuples() if latest is None or date.fromisoformat(r.date) > latest]
        db.bulk_save_objects(rows)
        db.commit()
        print(f"{name}: +{len(rows)} rows (was up to {latest}, now to {df.date.iloc[-1]})")
    db.close()


if __name__ == "__main__":
    main()
