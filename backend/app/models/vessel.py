from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class VesselClass(Base):
    """Handysize / Supramax / Panamax / Capesize reference specs — the DWT/LOA/
    beam/draft bands used by the compatibility engine to decide which classes a
    given port/berth can accept. Bands are documented as varying by up to
    ±5,000 DWT across industry sources (see research compendium, Section 2);
    we store one representative figure per class."""

    __tablename__ = "vessel_classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)

    dwt_min: Mapped[float] = mapped_column(Numeric(9, 1), nullable=False)
    dwt_max: Mapped[float] = mapped_column(Numeric(9, 1), nullable=False)

    typical_loa_m: Mapped[float | None] = mapped_column(Numeric(6, 2))
    typical_beam_m: Mapped[float | None] = mapped_column(Numeric(5, 2))
    typical_draft_m: Mapped[float | None] = mapped_column(Numeric(5, 2))

    vessels: Mapped[list["Vessel"]] = relationship(back_populates="vessel_class")


class Vessel(Base):
    """An individual vessel. For the hackathon prototype most rows will be
    synthetic (see Section 3's vessel-track simulator) rather than pulled from a
    paid AIS feed, and are clearly flagged as such via `is_synthetic`."""

    __tablename__ = "vessels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    imo: Mapped[str | None] = mapped_column(String(12), unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    vessel_class_id: Mapped[int] = mapped_column(ForeignKey("vessel_classes.id"), nullable=False)
    dwt: Mapped[float | None] = mapped_column(Numeric(9, 1))
    loa_m: Mapped[float | None] = mapped_column(Numeric(6, 2))
    beam_m: Mapped[float | None] = mapped_column(Numeric(5, 2))
    draft_m: Mapped[float | None] = mapped_column(Numeric(5, 2))

    flag: Mapped[str | None] = mapped_column(String(60))
    built_year: Mapped[int | None] = mapped_column(Integer)
    is_synthetic: Mapped[bool] = mapped_column(default=True)

    vessel_class: Mapped["VesselClass"] = relationship(back_populates="vessels")
