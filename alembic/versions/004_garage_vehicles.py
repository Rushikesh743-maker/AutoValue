"""Garage and portfolio intelligence schema additions

Revision ID: 004_garage_vehicles
Revises: 003_watchlist_and_vehicle_tracking
Create Date: 2026-10-09 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_garage_vehicles"
down_revision: Union[str, None] = "003_watchlist_and_vehicle_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "garage_vehicles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("valuation_id", sa.String(length=36), nullable=True),
        sa.Column("brand", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("variant", sa.String(length=128), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("fuel_type", sa.String(length=32), nullable=True, server_default="Petrol"),
        sa.Column("transmission", sa.String(length=32), nullable=True, server_default="Manual"),
        sa.Column("city", sa.String(length=64), nullable=True, server_default="Bengaluru"),
        sa.Column("nickname", sa.String(length=64), nullable=True),
        sa.Column("ownership_status", sa.String(length=32), nullable=False, server_default="OWNED"),
        sa.Column("purchase_price", sa.Float(), nullable=True),
        sa.Column("purchase_date", sa.DateTime(), nullable=True),
        sa.Column("current_odometer", sa.Integer(), nullable=True, server_default="35000"),
        sa.Column("annual_km", sa.Integer(), nullable=True, server_default="12000"),
        sa.Column("ownership_purpose", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["valuation_id"], ["saved_valuations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_garage_vehicles_id"), "garage_vehicles", ["id"], unique=False)
    op.create_index(op.f("ix_garage_vehicles_user_id"), "garage_vehicles", ["user_id"], unique=False)
    op.create_index(op.f("ix_garage_vehicles_valuation_id"), "garage_vehicles", ["valuation_id"], unique=False)
    op.create_index(op.f("ix_garage_vehicles_ownership_status"), "garage_vehicles", ["ownership_status"], unique=False)
    op.create_index(op.f("ix_garage_vehicles_created_at"), "garage_vehicles", ["created_at"], unique=False)
    op.create_index("ix_garage_vehicles_user_status", "garage_vehicles", ["user_id", "ownership_status"], unique=False)
    op.create_index("ix_garage_vehicles_user_created", "garage_vehicles", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_garage_vehicles_user_created", table_name="garage_vehicles")
    op.drop_index("ix_garage_vehicles_user_status", table_name="garage_vehicles")
    op.drop_index(op.f("ix_garage_vehicles_created_at"), table_name="garage_vehicles")
    op.drop_index(op.f("ix_garage_vehicles_ownership_status"), table_name="garage_vehicles")
    op.drop_index(op.f("ix_garage_vehicles_valuation_id"), table_name="garage_vehicles")
    op.drop_index(op.f("ix_garage_vehicles_user_id"), table_name="garage_vehicles")
    op.drop_index(op.f("ix_garage_vehicles_id"), table_name="garage_vehicles")
    op.drop_table("garage_vehicles")
