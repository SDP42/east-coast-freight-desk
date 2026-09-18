"""Seed the four documented disruption case studies from our own research
(Section 3.5 of the compendium) into `disruption_events` — real events, not
synthetic, used to bootstrap the Risk & Disruption Scoring module (Section 9).

Run from the backend venv: ../backend/.venv/bin/python3 seed_disruption_events.py
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models import DisruptionEvent  # noqa: E402

EVENTS = [
    dict(
        start_date=date(2023, 11, 1), end_date=date(2024, 6, 30),
        category="geopolitical", region="Suez Canal / Red Sea",
        title="Red Sea / Suez rerouting",
        description=(
            "Houthi attacks forced widespread rerouting via the Cape of Good Hope, adding "
            "~3,500 nautical miles and 10-14 days per affected voyage. Cape-routed tonnage "
            "rose ~60% while Suez container tonnage fell ~82% by early Feb 2024."
        ),
        impact_score=8.0,
        source_url="https://www.imf.org/Blogs/Articles/2024/03/07/Red-Sea-Attacks-Disrupt-Global-Trade",
    ),
    dict(
        start_date=date(2023, 7, 1), end_date=date(2024, 8, 31),
        category="canal_strait", region="Panama Canal",
        title="Panama Canal drought draft restriction",
        description=(
            "Permitted draft cut to 13.3m from a normal ~15m; daily transits fell from 36-38/day "
            "(Jul 2023) to 18/day (Feb 2024). FY2024 transits fell 29% to 9,936 vs 12,638 in FY2023. "
            "Not a direct India East Coast chokepoint, but reallocated global dry bulk tonnage and "
            "pressured rates market-wide."
        ),
        impact_score=6.0,
        source_url="https://www.bts.gov/data-spotlight/us-trade-and-impact-low-water-levels-gatun-lake-and-panama-canal",
    ),
    dict(
        start_date=date(2026, 1, 6), end_date=date(2026, 1, 13),
        category="weather", region="Queensland, Australia",
        title="Cyclone Koji — Dalrymple Bay Coal Terminal closure",
        description=(
            "Dalrymple Bay Coal Terminal stopped berthing vessels for roughly a week; force "
            "majeure declared by multiple coal producers. Echoes the 2017 Cyclone Debbie closure "
            "of all four major Queensland coal terminals — a recurring, seasonal, forecastable risk "
            "specific to Australian-origin coking coal supply."
        ),
        impact_score=5.0,
        source_url="https://discoveryalert.com.au/australia-coal-infrastructure-weather-2026/",
    ),
    dict(
        start_date=date(2022, 8, 1), end_date=date(2024, 12, 31),
        category="sanctions", region="Russia / Asia",
        title="EU ban on Russian coal — trade redirection",
        description=(
            "Following the EU's 2022 coal ban, Asia's share of Russian coal exports rose to ~84% "
            "by 2023 while Europe's share fell to ~13% by 2024. Freight to India spiked to ~$120/t "
            "on the Ust-Luga-west coast India route in March 2022 (vs $12-16/t on comparable routes) "
            "as insurance and reflagging costs surged."
        ),
        impact_score=7.0,
        source_url="https://www.argusmedia.com/en/news-and-insights/market-opinion-and-analysis-blog/weight-of-freight-how-expensive-is-shipping-russian-coal",
    ),
]


def main() -> None:
    db = SessionLocal()
    if db.query(DisruptionEvent).count():
        print("Disruption events already seeded — skipping.")
        db.close()
        return

    for spec in EVENTS:
        db.add(DisruptionEvent(**spec))
    db.commit()
    print(f"Seeded {len(EVENTS)} documented disruption events.")
    db.close()


if __name__ == "__main__":
    main()
