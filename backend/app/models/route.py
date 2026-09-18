from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Route(Base):
    """An origin-country/port to East-Coast-destination-port trade lane — the
    five origins named in the problem statement (Australia, US, Mozambique,
    Russia, Indonesia) each map to one or more of these rows per destination
    port, and freight rates / disruption events are analysed per route."""

    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    origin_port_id: Mapped[int] = mapped_column(ForeignKey("ports.id"), nullable=False)
    destination_port_id: Mapped[int] = mapped_column(ForeignKey("ports.id"), nullable=False)

    distance_nm: Mapped[float | None] = mapped_column(Numeric(8, 1))
    typical_transit_days: Mapped[float | None] = mapped_column(Numeric(5, 1))
    primary_commodity: Mapped[str | None] = mapped_column(String(60))
    """e.g. 'coking coal', 'thermal coal' — the two streams move on different
    vessel-size profiles per our research (Section 2 of the compendium)."""

    origin_port: Mapped["Port"] = relationship(foreign_keys=[origin_port_id])
    destination_port: Mapped["Port"] = relationship(foreign_keys=[destination_port_id])
