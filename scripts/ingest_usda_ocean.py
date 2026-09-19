"""Ingest the USDA Agricultural Marketing Service monthly ocean freight rates for grain (U.S. Gulf to Japan and U.S. Pacific
Northwest to Japan, US$ per tonne), January 1996 to the latest month.

Source: USDA AMS Grain Transportation Report datasets, "Figure 20: Grain vessel rates, U.S. to Japan" (GTRFigure20.xlsx). USDA
publishes it as non-confidential and non-copyrighted; the rates are compiled by O'Neil Commodity Consulting and credited on the
sheet. These are grain-vessel (Panamax and Supramax) rates, a market proxy for dry-bulk freight, not coal rates.
The sheet mixes date styles ("96-Jan", "Mar. 02", "Jun '18", ISO dates) and has a typo year (1919 for 2019); the parser handles them.
"""

import io
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import func  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import FreightRate  # noqa: E402

URL = "https://www.ams.usda.gov/sites/default/files/media/GTRFigure20.xlsx"
SOURCE = "USDA AMS Grain Transportation Report, Figure 20 (rates by O'Neil Commodity Consulting)"
MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def parse_month(cell) -> date | None:
    s = str(cell).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        t = pd.to_datetime(s[:10])
        return date(2019 if t.year == 1919 else t.year, t.month, 1)
    m = re.match(r"^(\d\d)-([A-Za-z]+)$", s)
    if m:
        yy, mon = int(m.group(1)), m.group(2)
    else:
        m = re.match(r"^([A-Za-z]+)\.?\s*'?(\d\d)$", s)
        if not m:
            return None
        mon, yy = m.group(1), int(m.group(2))
    month = MONTHS.get(mon.lower()[:3])
    return date(1900 + yy if yy >= 90 else 2000 + yy, month, 1) if month else None


def fetch() -> dict[str, dict[date, float]]:
    raw = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (freight-desk research prototype)"}), timeout=90).read()
    df = pd.read_excel(io.BytesIO(raw), sheet_name="Data", header=None)
    out: dict[str, dict[date, float]] = {"OCEAN_GULF_JAPAN": {}, "OCEAN_PNW_JAPAN": {}}
    for r in df.iloc[6:].itertuples(index=False):
        d = parse_month(r[0])
        if d is None:
            continue
        for name, col in (("OCEAN_GULF_JAPAN", 1), ("OCEAN_PNW_JAPAN", 3)):
            try:
                v = float(r[col])
            except (TypeError, ValueError):
                continue
            if v == v and v > 0:
                out[name][d] = v
    return out


def main() -> None:
    data = fetch()
    db = SessionLocal()
    for name, series in data.items():
        db.query(FreightRate).filter(FreightRate.index_name == name).delete()
        db.bulk_save_objects([FreightRate(rate_date=d, index_name=name, value=v, unit="usd_per_tonne", source=SOURCE) for d, v in sorted(series.items())])
        db.commit()
        ks = sorted(series)
        print(f"{name}: {len(series)} months, {ks[0]} to {ks[-1]}, latest {series[ks[-1]]}")
    db.close()


if __name__ == "__main__":
    main()
