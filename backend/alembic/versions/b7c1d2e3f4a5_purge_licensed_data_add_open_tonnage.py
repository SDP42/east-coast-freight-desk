"""Remove the tables that held licensed or unclear-licence data, and add open tonnage (user-supplied broker lists).

Revision ID: b7c1d2e3f4a5
Revises: 685bac874698
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "685bac874698"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for t in ("haldia_coal_calls", "port_activity", "chokepoint_transits"):
        op.execute(f"DROP TABLE IF EXISTS {t}")
    op.create_table(
        "open_tonnage",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), index=True),
        sa.Column("vessel_name", sa.String(120), nullable=False),
        sa.Column("imo", sa.String(12)),
        sa.Column("dwt", sa.Integer, nullable=False),
        sa.Column("loa_m", sa.Numeric(6, 1)),
        sa.Column("beam_m", sa.Numeric(5, 1)),
        sa.Column("draft_m", sa.Numeric(5, 2)),
        sa.Column("open_port", sa.String(80), nullable=False),
        sa.Column("open_date", sa.Date, nullable=False),
        sa.Column("speed_knots", sa.Numeric(4, 1)),
        sa.Column("broker", sa.String(120)),
        sa.Column("notes", sa.Text, server_default=""),
        sa.Column("is_sample", sa.Boolean, server_default=sa.false()),
        sa.Column("uploaded_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("open_tonnage")
