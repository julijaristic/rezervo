"""Radno vreme na venues tabeli.

Revision ID: 20260329_opening_hours
Revises:
Create Date: 2026-03-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260329_opening_hours"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "venues" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("venues")}
    if "weekday_open" not in cols:
        op.add_column("venues", sa.Column("weekday_open", sa.Time(), nullable=False, server_default="10:00:00"))
    if "weekday_close" not in cols:
        op.add_column("venues", sa.Column("weekday_close", sa.Time(), nullable=False, server_default="22:00:00"))
    if "weekend_open" not in cols:
        op.add_column("venues", sa.Column("weekend_open", sa.Time(), nullable=False, server_default="10:00:00"))
    if "weekend_close" not in cols:
        op.add_column("venues", sa.Column("weekend_close", sa.Time(), nullable=False, server_default="22:00:00"))


def downgrade() -> None:
    op.drop_column("venues", "weekend_close")
    op.drop_column("venues", "weekend_open")
    op.drop_column("venues", "weekday_close")
    op.drop_column("venues", "weekday_open")
