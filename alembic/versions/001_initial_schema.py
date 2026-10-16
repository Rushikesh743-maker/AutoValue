"""Initial schema for AutoValue

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-02 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sources table
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sources_id"), "sources", ["id"], unique=False)
    op.create_index(op.f("ix_sources_name"), "sources", ["name"], unique=True)

    # Create collection_runs table
    op.create_table(
        "collection_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("records_collected", sa.Integer(), nullable=False, default=0),
        sa.Column("records_valid", sa.Integer(), nullable=False, default=0),
        sa.Column("records_rejected", sa.Integer(), nullable=False, default=0),
        sa.Column("status", sa.String(length=32), nullable=False, default="started"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_collection_runs_id"), "collection_runs", ["id"], unique=False)
    op.create_index(op.f("ix_collection_runs_source_id"), "collection_runs", ["source_id"], unique=False)

    # Create car_listings table
    op.create_table(
        "car_listings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("listing_id", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("listing_url", sa.String(length=1024), nullable=True),
        sa.Column("brand", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("variant", sa.String(length=128), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("fuel_type", sa.String(length=32), nullable=True),
        sa.Column("transmission", sa.String(length=32), nullable=True),
        sa.Column("km_driven", sa.Integer(), nullable=True),
        sa.Column("engine_cc", sa.Integer(), nullable=True),
        sa.Column("mileage", sa.Float(), nullable=True),
        sa.Column("owner_count", sa.Integer(), nullable=True),
        sa.Column("city", sa.String(length=64), nullable=True),
        sa.Column("state", sa.String(length=64), nullable=True),
        sa.Column("seller_type", sa.String(length=64), nullable=True),
        sa.Column("listed_price", sa.Float(), nullable=False),
        sa.Column("date_collected", sa.DateTime(), nullable=False),
        sa.Column("is_duplicate_candidate", sa.Boolean(), nullable=False, default=False),
        sa.Column("duplicate_similarity", sa.Float(), nullable=True),
        sa.Column("duplicate_of_id", sa.Integer(), nullable=True),
        sa.Column("duplicate_notes", sa.String(length=512), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_car_listings_id"), "car_listings", ["id"], unique=False)
    op.create_index(op.f("ix_car_listings_listing_id"), "car_listings", ["listing_id"], unique=False)
    op.create_index(op.f("ix_car_listings_source"), "car_listings", ["source"], unique=False)
    op.create_index(op.f("ix_car_listings_brand"), "car_listings", ["brand"], unique=False)
    op.create_index(op.f("ix_car_listings_model"), "car_listings", ["model"], unique=False)
    op.create_index(op.f("ix_car_listings_year"), "car_listings", ["year"], unique=False)
    op.create_index(op.f("ix_car_listings_city"), "car_listings", ["city"], unique=False)
    op.create_index(op.f("ix_car_listings_date_collected"), "car_listings", ["date_collected"], unique=False)
    op.create_index(op.f("ix_car_listings_is_duplicate_candidate"), "car_listings", ["is_duplicate_candidate"], unique=False)
    
    # Composite indexes
    op.create_index("ix_listings_brand_model_year", "car_listings", ["brand", "model", "year"], unique=False)
    op.create_index("ix_listings_brand_model_city", "car_listings", ["brand", "model", "city"], unique=False)
    op.create_index("ix_listings_brand_model_date", "car_listings", ["brand", "model", "date_collected"], unique=False)
    op.create_index("ix_listings_source_listing_id", "car_listings", ["source", "listing_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_listings_source_listing_id", table_name="car_listings")
    op.drop_index("ix_listings_brand_model_date", table_name="car_listings")
    op.drop_index("ix_listings_brand_model_city", table_name="car_listings")
    op.drop_index("ix_listings_brand_model_year", table_name="car_listings")
    op.drop_index(op.f("ix_car_listings_is_duplicate_candidate"), table_name="car_listings")
    op.drop_index(op.f("ix_car_listings_date_collected"), table_name="car_listings")
    op.drop_index(op.f("ix_car_listings_city"), table_name="car_listings")
    op.drop_index(op.f("ix_car_listings_year"), table_name="car_listings")
    op.drop_index(op.f("ix_car_listings_model"), table_name="car_listings")
    op.drop_index(op.f("ix_car_listings_brand"), table_name="car_listings")
    op.drop_index(op.f("ix_car_listings_source"), table_name="car_listings")
    op.drop_index(op.f("ix_car_listings_listing_id"), table_name="car_listings")
    op.drop_index(op.f("ix_car_listings_id"), table_name="car_listings")
    op.drop_table("car_listings")

    op.drop_index(op.f("ix_collection_runs_source_id"), table_name="collection_runs")
    op.drop_index(op.f("ix_collection_runs_id"), table_name="collection_runs")
    op.drop_table("collection_runs")

    op.drop_index(op.f("ix_sources_name"), table_name="sources")
    op.drop_index(op.f("ix_sources_id"), table_name="sources")
    op.drop_table("sources")
