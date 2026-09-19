"""Loading-port (origin) constraints for the five coking-coal origins, so a ship must fit BOTH ends of the voyage.

Figures are as published by the terminals, port authorities or port guides listed in `source`. One representative coal-loading
terminal per origin is used, because that is where SAIL's coking coal actually loads. They are planning limits, not
berth-by-berth data: check the terminal's own notice before fixing. Safe to re-run (updates in place).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Port  # noqa: E402

# country -> (name, lat, lon, max_draft_m, max_loa_m, max_beam_m, source)
ORIGINS = {
    "Australia": ("Hay Point / Dalrymple Bay", -21.28, 149.30, 17.5, 300.0, 56.0,
                  "NQBP berths and wharf capability (nqbp.com.au/trade/berths-and-wharf-capability); DBCT shipping page (dbct.com.au/shipping): max LOA 300 m, beam 56 m, draught 17.5 m, 200,000 DWT"),
    "United States": ("Hampton Roads (Lamberts Point)", 36.95, -76.33, 15.2, None, 53.0,
                      "Norfolk Southern Lamberts Point terminal: loads to 50 ft at high tide, pier beam up to 174 ft; Norfolk Harbor channel 55 ft (Virginia Maritime Association port facilities guide; NOAA Coast Pilot 3)"),
    "Mozambique": ("Nacala (Beira alternative)", -14.47, 40.69, 14.0, None, None,
                   "Nacala pier 9 to 14 m draft, access channel 800 m wide and 60 m deep (africaports.co.za/nacala; Global Energy Monitor); Beira is limited to about 12 m and Maputo to about 11 m alongside"),
    "Russia": ("Vostochny (Ust-Luga alternative)", 42.72, 133.07, 16.0, 300.0, None,
               "Vostochny Port coal section: Capesize up to 300 m LOA, 190,000 DWT, laden draft 16.0 m (Vostochny Port / Nakhodka Maritime Services); Ust-Luga coal terminal permits 12.7 to 14.55 m and about 110,000 DWT"),
    "Indonesia": ("Balikpapan (Kalimantan)", -1.27, 116.83, 13.0, 250.0, 43.0,
                  "Balikpapan Coal Terminal: LOA 250 m, beam 43 m, draught about 13.0 m, 80,000 DWT normal (up to 160,000 DWT with tide); Kalimantan cargoes are often loaded by barge and transhipped at anchorage"),
}


def main() -> None:
    db = SessionLocal()
    for country, (name, lat, lon, draft, loa, beam, source) in ORIGINS.items():
        p = db.query(Port).filter(Port.country == country, Port.is_destination.is_(False)).first()
        if p is None:
            print(f"{country}: no origin port row found; skipped")
            continue
        p.name, p.latitude, p.longitude, p.max_draft_m, p.max_loa_m, p.max_beam_m, p.source = name, lat, lon, draft, loa, beam, source
        print(f"{country}: {name}, draft {draft} m, LOA {loa}, beam {beam}")
    db.commit()
    db.close()


if __name__ == "__main__":
    main()
