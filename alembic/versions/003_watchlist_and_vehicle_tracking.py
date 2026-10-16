"""Watchlist and vehicle tracking schema additions

Revision ID: 003_watchlist_and_vehicle_tracking
Revises: 002_user_auth_and_saved_valuations
Create Date: 2026-10-07 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_watchlist_and_vehicle_tracking"
down_revision: Union[str, None] = "002_user_auth_and_saved_valuations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add watchlist tracking columns to saved_vehicles
    op.add_column("saved_vehicles", sa.Column("watch_status", sa.String(length=32), nullable=True, server_default="watching"))
    op.add_column("saved_vehicles", sa.Column("last_checked_at", sa.DateTime(), nullable=True))
    op.add_column("saved_vehicles", sa.Column("last_estimated_value", sa.Float(), nullable=True))
    op.add_column("saved_vehicles", sa.Column("previous_estimated_value", sa.Float(), nullable=True))
    op.create_index(op.f("ix_saved_vehicles_watch_status"), "saved_vehicles", ["watch_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_saved_vehicles_watch_status"), table_name="saved_vehicles")
    op.drop_column("saved_vehicles", "previous_estimated_value")
    op.drop_column("saved_vehicles", "last_estimated_value")
    op.drop_column("saved_vehicles", "last_checked_at")
    op.drop_column("saved_vehicles", "watch_status")
