"""Bring the market series up to date from FRED (Federal Reserve Bank of St. Louis), which serves public series with no key.

Adds what the 2012-2019 Baltic index history cannot give us: a current freight-cost signal and current coal and
iron-ore prices.
  WPU30130101  US BLS Producer Price Index, deep-sea freight (monthly, public domain)  -> DEEPSEA_PPI
  World Bank Commodity Markets "Pink Sheet" monthly file (to the latest month)          -> COAL_AUS, COAL_ZA (extends the existing series
                                                                                          on the same definition; FRED's IMF coal series uses a
                                                                                          different basis, so it is not mixed in)
  PIORECRUSDM  Iron ore, US$/t                                                          -> IRON_ORE
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
    ("PIORECRUSDM", "IRON_ORE", "usd_per_tonne", "IMF primary commodity prices via FRED"),
]


def fetch(series_id: str) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (freight-desk research prototype)"})
    text = urllib.request.urlopen(req, timeout=60).read().decode()
    df = pd.read_csv(io.StringIO(text))
    df.columns = ["date", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna()


WB_URL = "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx"
WB_SOURCE = "World Bank Commodity Markets (Pink Sheet), Monthly Prices"
WB_COLUMNS = {"Coal, Australian": "COAL_AUS", "Coal, South African **": "COAL_ZA"}


def extend_from_world_bank(db) -> None:
    req = urllib.request.Request(WB_URL, headers={"User-Agent": "Mozilla/5.0 (freight-desk research prototype)"})
    raw = urllib.request.urlopen(req, timeout=120).read()
    df = pd.read_excel(io.BytesIO(raw), sheet_name="Monthly Prices", skiprows=4)
    df = df.rename(columns={df.columns[0]: "period"})
    df = df[df["period"].astype(str).str.match(r"^\d{4}M\d{2}$", na=False)]
    # Remove any earlier rows for these series that came from a different source, so the level is consistent.
    for name in WB_COLUMNS.values():
        db.query(FreightRate).filter(FreightRate.index_name == name, FreightRate.source != WB_SOURCE).delete()
    db.commit()
    for col, name in WB_COLUMNS.items():
        latest = db.query(func.max(FreightRate.rate_date)).filter(FreightRate.index_name == name).scalar()
        rows = []
        for r in df.itertuples():
            y, m = r.period.split("M")
            d = date(int(y), int(m), 1)
            v = pd.to_numeric(getattr(r, "_" + str(list(df.columns).index(col))), errors="coerce")
            if pd.notna(v) and (latest is None or d > latest):
                rows.append(FreightRate(rate_date=d, index_name=name, value=float(v), unit="usd_per_tonne", source=WB_SOURCE))
        db.bulk_save_objects(rows)
        db.commit()
        print(f"{name}: +{len(rows)} rows from the World Bank file (was up to {latest})")


def main() -> None:
    db = SessionLocal()
    try:
        extend_from_world_bank(db)
    except Exception as e:  # noqa: BLE001
        print(f"World Bank coal file: could not update ({e}); left unchanged")
    for fred_id, name, unit, source in SERIES:
        try:
            df = fetch(fred_id)
        except Exception as e:  # noqa: BLE001
            print(f"{name}: could not fetch {fred_id} ({e}); left unchanged")
            continue
        latest = db.query(func.max(FreightRate.rate_date)).filter(FreightRate.index_name == name).scalar()
        rows = [
            FreightRate(rate_date=date.fromisoformat(r.date), index_name=name, value=float(r.value), unit=unit, source=source)
            for r in df.itertuples() if latest is None or date.fromisoformat(r.date) > latest
        ]
        db.bulk_save_objects(rows)
        db.commit()
        print(f"{name}: +{len(rows)} rows (was up to {latest}, now to {df.date.iloc[-1]})")
    db.close()


if __name__ == "__main__":
    main()
