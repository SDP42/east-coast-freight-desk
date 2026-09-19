"""Derive per-port, per-month cyclone exposure from IBTrACS North Indian Ocean best tracks (NOAA NCEI,
public domain; cite Knapp et al. 2010). For 1990-2025: share of days with a storm (>=34 kt) centred
within 400 km of the port, share with a severe storm (>=64 kt), and distinct storms per year."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import CycloneExposure, Port  # noqa: E402
import _download  # noqa: E402

FILE = Path(__file__).resolve().parents[1] / "data" / "raw" / "candidates" / "ibtracs_NI.csv"
RADIUS_KM = 400
Y0, Y1 = 1990, 2025


def haversine(lat1, lon1, lat2, lon2):
    p = np.pi / 180
    a = np.sin((lat2 - lat1) * p / 2) ** 2 + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2
    return 12742 * np.arcsin(np.sqrt(a))


def main() -> None:
    if not _download.ensure(FILE, "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NI.list.v04r01.csv", "NOAA IBTrACS North Indian Ocean tracks (28 MB)"):
        print("IBTrACS file not available - skipping.")
        return
    df = pd.read_csv(FILE, skiprows=[1], usecols=["SID", "ISO_TIME", "LAT", "LON", "WMO_WIND", "USA_WIND"], low_memory=False)
    df["time"] = pd.to_datetime(df["ISO_TIME"], errors="coerce")
    for c in ("LAT", "LON", "WMO_WIND", "USA_WIND"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["wind"] = df[["WMO_WIND", "USA_WIND"]].max(axis=1)
    df = df.dropna(subset=["time", "LAT", "LON", "wind"])
    df = df[(df.time.dt.year >= Y0) & (df.time.dt.year <= Y1) & (df.wind >= 34)]
    df["day"] = df.time.dt.normalize()

    db = SessionLocal()
    db.query(CycloneExposure).delete()
    years = Y1 - Y0 + 1
    days_in_month = {m: pd.Period(f"2001-{m:02d}").days_in_month for m in range(1, 13)}
    for port in db.query(Port).filter(Port.is_destination.is_(True), Port.latitude.isnot(None)).all():
        d = haversine(float(port.latitude), float(port.longitude), df.LAT.values, df.LON.values)
        near = df[d <= RADIUS_KM]
        for m in range(1, 13):
            nm = near[near.time.dt.month == m]
            storm_days = nm.day.nunique()
            severe_days = nm[nm.wind >= 64].day.nunique()
            denom = years * days_in_month[m]
            db.add(CycloneExposure(port_name=port.name, month=m, storm_day_prob=storm_days / denom, severe_day_prob=severe_days / denom,
                                   storms_per_year=nm.SID.nunique() / years, years=years))
    db.commit()
    print(f"Wrote cyclone exposure for {db.query(CycloneExposure).count() // 12} ports x 12 months from {len(df)} track points.")
    db.close()


if __name__ == "__main__":
    main()
