"""User authentication, saved valuations, saved vehicles, and share tokens schema

Revision ID: 002_user_auth_and_saved_valuations
Revises: 001_initial_schema
Create Date: 2026-10-03 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_user_auth_and_saved_valuations"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_created_at"), "users", ["created_at"], unique=False)

    # 2. Create saved_valuations table
    op.create_table(
        "saved_valuations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("brand", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("variant", sa.String(length=128), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("fuel_type", sa.String(length=32), nullable=True),
        sa.Column("transmission", sa.String(length=32), nullable=True),
        sa.Column("km_driven", sa.Integer(), nullable=False),
        sa.Column("city", sa.String(length=64), nullable=False),
        sa.Column("engine_cc", sa.Integer(), nullable=True),
        sa.Column("mileage", sa.Float(), nullable=True),
        sa.Column("owner_count", sa.Integer(), nullable=True),
        sa.Column("seller_type", sa.String(length=64), nullable=True),
        sa.Column("asking_price", sa.Float(), nullable=True),
        sa.Column("estimated_value", sa.Float(), nullable=False),
        sa.Column("range_low", sa.Float(), nullable=True),
        sa.Column("range_high", sa.Float(), nullable=True),
        sa.Column("model_interval_low", sa.Float(), nullable=True),
        sa.Column("model_interval_high", sa.Float(), nullable=True),
        sa.Column("market_median", sa.Float(), nullable=True),
        sa.Column("comparable_count", sa.Integer(), nullable=False, default=0),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("dataset_version", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("notes", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_saved_valuations_id"), "saved_valuations", ["id"], unique=False)
    op.create_index(op.f("ix_saved_valuations_user_id"), "saved_valuations", ["user_id"], unique=False)
    op.create_index(op.f("ix_saved_valuations_created_at"), "saved_valuations", ["created_at"], unique=False)
    op.create_index(op.f("ix_saved_valuations_brand"), "saved_valuations", ["brand"], unique=False)
    op.create_index(op.f("ix_saved_valuations_model"), "saved_valuations", ["model"], unique=False)
    op.create_index("ix_saved_valuations_user_created", "saved_valuations", ["user_id", "created_at"], unique=False)
    op.create_index("ix_saved_valuations_brand_model", "saved_valuations", ["brand", "model"], unique=False)

    # 3. Create saved_vehicles table
    op.create_table(
        "saved_vehicles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("brand", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("variant", sa.String(length=128), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("fuel_type", sa.String(length=32), nullable=True),
        sa.Column("transmission", sa.String(length=32), nullable=True),
        sa.Column("km_driven", sa.Integer(), nullable=False),
        sa.Column("city", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "brand", "model", "variant", "year", "fuel_type", "transmission", "km_driven", "city",
            name="uq_user_saved_vehicle_fingerprint"
        )
    )
    op.create_index(op.f("ix_saved_vehicles_id"), "saved_vehicles", ["id"], unique=False)
    op.create_index(op.f("ix_saved_vehicles_user_id"), "saved_vehicles", ["user_id"], unique=False)
    op.create_index(op.f("ix_saved_vehicles_created_at"), "saved_vehicles", ["created_at"], unique=False)
    op.create_index("ix_saved_vehicles_user_created", "saved_vehicles", ["user_id", "created_at"], unique=False)

    # 4. Create share_tokens table
    op.create_table(
        "share_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("valuation_id", sa.String(length=36), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, default=0),
        sa.ForeignKeyConstraint(["valuation_id"], ["saved_valuations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_share_tokens_id"), "share_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_share_tokens_valuation_id"), "share_tokens", ["valuation_id"], unique=True)
    op.create_index(op.f("ix_share_tokens_token"), "share_tokens", ["token"], unique=True)
    op.create_index("ix_share_tokens_token_active", "share_tokens", ["token", "is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_share_tokens_token_active", table_name="share_tokens")
    op.drop_index(op.f("ix_share_tokens_token"), table_name="share_tokens")
    op.drop_index(op.f("ix_share_tokens_valuation_id"), table_name="share_tokens")
    op.drop_index(op.f("ix_share_tokens_id"), table_name="share_tokens")
    op.drop_table("share_tokens")

    op.drop_index("ix_saved_vehicles_user_created", table_name="saved_vehicles")
    op.drop_index(op.f("ix_saved_vehicles_created_at"), table_name="saved_vehicles")
    op.drop_index(op.f("ix_saved_vehicles_user_id"), table_name="saved_vehicles")
    op.drop_index(op.f("ix_saved_vehicles_id"), table_name="saved_vehicles")
    op.drop_table("saved_vehicles")

    op.drop_index("ix_saved_valuations_brand_model", table_name="saved_valuations")
    op.drop_index("ix_saved_valuations_user_created", table_name="saved_valuations")
    op.drop_index(op.f("ix_saved_valuations_model"), table_name="saved_valuations")
    op.drop_index(op.f("ix_saved_valuations_brand"), table_name="saved_valuations")
    op.drop_index(op.f("ix_saved_valuations_created_at"), table_name="saved_valuations")
    op.drop_index(op.f("ix_saved_valuations_user_id"), table_name="saved_valuations")
    op.drop_index(op.f("ix_saved_valuations_id"), table_name="saved_valuations")
    op.drop_table("saved_valuations")

    op.drop_index(op.f("ix_users_created_at"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
