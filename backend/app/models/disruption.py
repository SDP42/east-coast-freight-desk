from datetime import date

from sqlalchemy import Date, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DisruptionEvent(Base):
    """A supply-chain disruption event feeding the Risk & Disruption Scoring
    module (Section 9, feature #6) — seeded initially from the four documented
    case studies in our research (Red Sea/Suez, Panama Canal drought,
    Australian cyclone season, Russia sanctions/trade redirection), extendable
    with a live weather/news feed later."""

    __tablename__ = "disruption_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date | None] = mapped_column(Date)

    category: Mapped[str] = mapped_column(String(30), nullable=False)
    """'weather', 'geopolitical', 'canal_strait', 'sanctions', 'port_congestion'."""

    region: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    impact_score: Mapped[float | None] = mapped_column(Numeric(4, 2))
    """0-10 analyst/derived severity score, used as an input to the composite
    Route Risk Score."""

    source_url: Mapped[str | None] = mapped_column(String(300))
