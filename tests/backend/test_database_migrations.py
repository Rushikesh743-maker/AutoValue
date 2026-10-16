"""
Unit & Integration Tests for Database Migrations (Task 4 & 5).
Validates full Alembic migration chain from clean disposable database,
incremental upgrade from 003 to 004, downgrade from 004 to 003,
and schema integrity of the garage_vehicles table.
"""
import os
import tempfile
import pytest
from sqlalchemy import create_engine, inspect
from alembic.config import Config
from alembic import command


@pytest.fixture
def disposable_db_url():
    """Create a temporary disposable SQLite file database for migration testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    url = f"sqlite:///{db_path}"
    yield url
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass


def get_alembic_config(db_url: str) -> Config:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ini_path = os.path.join(repo_root, "alembic.ini")
    cfg = Config(ini_path)
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.set_main_option("script_location", os.path.join(repo_root, "alembic"))
    return cfg


def test_full_migration_chain_from_scratch(disposable_db_url):
    """Verify running all migrations from an empty database creates all tables successfully."""
    cfg = get_alembic_config(disposable_db_url)
    command.upgrade(cfg, "head")

    engine = create_engine(disposable_db_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # All expected tables must exist
    assert "users" in tables
    assert "sources" in tables
    assert "car_listings" in tables
    assert "saved_valuations" in tables
    assert "saved_vehicles" in tables
    assert "share_tokens" in tables
    assert "garage_vehicles" in tables

    # Verify garage_vehicles columns and indexes
    columns = {col["name"]: col for col in inspector.get_columns("garage_vehicles")}
    assert "id" in columns
    assert "user_id" in columns
    assert "brand" in columns
    assert "model" in columns
    assert "year" in columns
    assert "ownership_status" in columns
    assert "current_odometer" in columns
    assert "annual_km" in columns

    # Verify indexes
    indexes = {idx["name"] for idx in inspector.get_indexes("garage_vehicles")}
    assert "ix_garage_vehicles_id" in indexes
    assert "ix_garage_vehicles_user_id" in indexes
    assert "ix_garage_vehicles_ownership_status" in indexes
    assert "ix_garage_vehicles_user_status" in indexes


def test_incremental_upgrade_003_to_004(disposable_db_url):
    """Verify upgrading a database already at revision 003 cleanly transitions to 004."""
    cfg = get_alembic_config(disposable_db_url)
    
    # First upgrade up to 003
    command.upgrade(cfg, "003")
    engine = create_engine(disposable_db_url)
    inspector = inspect(engine)
    assert "garage_vehicles" not in inspector.get_table_names()

    # Now upgrade to head (004)
    command.upgrade(cfg, "004")
    inspector = inspect(engine)
    assert "garage_vehicles" in inspector.get_table_names()


def test_migration_downgrade_and_reupgrade(disposable_db_url):
    """Verify downgrading revision 004 to 003 drops the table, and re-upgrading restores it."""
    cfg = get_alembic_config(disposable_db_url)
    command.upgrade(cfg, "head")

    engine = create_engine(disposable_db_url)
    inspector = inspect(engine)
    assert "garage_vehicles" in inspector.get_table_names()

    # Downgrade 004 -> 003
    command.downgrade(cfg, "-1")
    inspector = inspect(engine)
    assert "garage_vehicles" not in inspector.get_table_names()

    # Re-upgrade 003 -> 004
    command.upgrade(cfg, "head")
    inspector = inspect(engine)
    assert "garage_vehicles" in inspector.get_table_names()
