"""Parse SMP Kolkata's Haldia Dock Complex daily 'Morning Position' PDFs (public, Government of India
port authority publication) into `haldia_coal_calls`: coking-coal and PCI-coal vessels with LOA,
expected draft, cargo tonnage and importer group. Needs `pdftotext` (poppler). Raw PDFs live in
data/raw/haldia/ (gitignored); the script skips quietly if there are none.
"""

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import HaldiaCoalCall  # noqa: E402

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "haldia"
ID = r"(INHAL\d{9,}|HAL\d{7,}R?)"
COAL = re.compile(r"(coking\s*coal|pci\s*coal)", re.I)
NAME_ID = re.compile(rf"(?:M\.V\.\s+)?([A-Z][A-Za-z0-9 .'\-]+?)\s*\[?{ID}\]?")
NUM = re.compile(r"\b(\d{2,3},?\d{3})\b")


def group(line: str) -> str:
    low = line.lower()
    if "sail" in low or "steel authority" in low:
        return "SAIL"
    if "tata" in low or "tmill" in low:
        return "Tata Steel"
    return "Other"


def parse(text: str, report_date: date) -> list[dict]:
    rows = []
    for line in text.splitlines():
        if not COAL.search(line):
            continue
        m = NAME_ID.search(line)
        if not m:
            continue
        rest = line[m.end():]
        floats = re.findall(r"\b(\d{1,3}\.\d{2})\b", rest)
        loa = next((float(f) for f in floats if float(f) > 100), None)
        draft = next((float(f) for f in floats if 5 < float(f) < 12), None)
        tonnage = None
        after = rest[COAL.search(rest).end():] if COAL.search(rest) else rest
        nums = [int(n.replace(",", "")) for n in NUM.findall(after)]
        nums = [n for n in nums if 5000 <= n <= 90000]
        if nums:
            tonnage = max(nums)
        origin = None
        om = re.search(r"\s(HAYPOINT|DALRYMPLE BAY|GLADSTONE|ABBOT POINT|HAY POINT|VISTINO|NAKHODKA|VOSTOCHNY|MAPUTO|BEIRA|NEWPORT NEWS|HAMPTON ROADS|BALTIMORE|MOBILE|ROSTERMIN|ROSTERMINAL)", line, re.I)
        if om:
            origin = om.group(1).title()
        rows.append({
            "vessel_id": m.group(2).rstrip("R"), "vessel_name": re.sub(r"\s+", " ", m.group(1).replace("M.V. ", "")).strip().title(),
            "first_report_date": report_date, "loa_m": loa, "expected_draft_m": draft,
            "cargo": "PCI coal" if "pci" in COAL.search(line).group(1).lower() else "Coking coal",
            "tonnage_t": tonnage, "importer_group": group(line), "origin_port": origin,
        })
    return rows


def main() -> None:
    files = sorted(RAW.glob("DP-*.pdf"))
    if not files:
        print("No Haldia morning-position PDFs in data/raw/haldia - skipping.")
        return
    best: dict[str, dict] = {}
    for f in files:
        d = f.stem[3:]
        report_date = date(int(d[4:]), int(d[2:4]), int(d[:2]))
        text = subprocess.run(["pdftotext", "-layout", str(f), "-"], capture_output=True, text=True).stdout
        for r in parse(text, report_date):
            cur = best.get(r["vessel_id"])
            if cur is None:
                best[r["vessel_id"]] = r
                continue
            r["first_report_date"] = min(cur["first_report_date"], r["first_report_date"])
            for k in ("loa_m", "expected_draft_m", "tonnage_t", "origin_port"):
                r[k] = r[k] if r[k] is not None else cur[k]
            if cur["importer_group"] != "Other" and r["importer_group"] == "Other":
                r["importer_group"] = cur["importer_group"]
            best[r["vessel_id"]] = r
    db = SessionLocal()
    db.query(HaldiaCoalCall).delete()
    db.bulk_save_objects([HaldiaCoalCall(**r) for r in best.values()])
    db.commit()
    db.close()
    print(f"Parsed {len(files)} reports into {len(best)} distinct coal vessels.")


if __name__ == "__main__":
    main()
