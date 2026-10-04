"""Broj stolova na venues tabeli.

Revision ID: 20261003_table_count
Revises: 20260329_opening_hours
Create Date: 2026-10-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261003_table_count"
down_revision: Union[str, None] = "20260329_opening_hours"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "venues" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("venues")}
    if "table_count" not in cols:
        op.add_column(
            "venues",
            sa.Column("table_count", sa.Integer(), nullable=False, server_default="30"),
        )


def downgrade() -> None:
    op.drop_column("venues", "table_count")
