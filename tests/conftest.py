"""Shared test fixtures — small SQLite databases with realistic data."""

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_epc_db(tmp_path: Path) -> Path:
    """Create a small EPC database with a few test rows."""
    db_path = tmp_path / "test_epc.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE epc_addresses (
            lmk_key TEXT PRIMARY KEY,
            postcode TEXT,
            address1 TEXT,
            address2 TEXT,
            address3 TEXT,
            address TEXT,
            uprn TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX idx_epc_postcode ON epc_addresses (postcode)"
    )
    rows = [
        (
            "lmk001",
            "SW1A 2AA",
            "10 DOWNING STREET",
            "",
            "",
            "10, DOWNING STREET, LONDON",
            "100023336956",
        ),
        (
            "lmk002",
            "SW1A 2AA",
            "11 DOWNING STREET",
            "",
            "",
            "11, DOWNING STREET, LONDON",
            "100023336957",
        ),
        (
            "lmk003",
            "EC1A 1BB",
            "1 EXAMPLE ROAD",
            "FLAT A",
            "",
            "FLAT A, 1 EXAMPLE ROAD, LONDON",
            "200000000001",
        ),
        (
            "lmk004",
            "M1 1AE",
            "50 HIGH STREET",
            "",
            "",
            "50, HIGH STREET, MANCHESTER",
            "300000000001",
        ),
        # Row with bad UPRN to test coercion handling
        (
            "lmk005",
            "SW1A 2AA",
            "12 DOWNING STREET",
            "",
            "",
            "12, DOWNING STREET, LONDON",
            "not_a_number",
        ),
    ]
    conn.executemany(
        "INSERT INTO epc_addresses VALUES (?, ?, ?, ?, ?, ?, ?)", rows
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture()
def tmp_os_db(tmp_path: Path) -> Path:
    """Create a small OS UPRN database with matching coordinates."""
    db_path = tmp_path / "test_os.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE uprns (
            UPRN INTEGER PRIMARY KEY,
            X_COORDINATE REAL,
            Y_COORDINATE REAL,
            LATITUDE REAL,
            LONGITUDE REAL
        )
        """
    )
    rows = [
        (100023336956, 530047.0, 179951.0, 51.5034, -0.1276),
        (100023336957, 530048.0, 179952.0, 51.5035, -0.1275),
        (200000000001, 532000.0, 181000.0, 51.5200, -0.1000),
        (300000000001, 383800.0, 398000.0, 53.4808, -2.2426),
    ]
    conn.executemany("INSERT INTO uprns VALUES (?, ?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture()
def client(tmp_epc_db: Path, tmp_os_db: Path):
    """Create a UKGeolocate client with test databases."""
    from ukgeolocate import UKGeolocate

    c = UKGeolocate(epc_db=tmp_epc_db, os_db=tmp_os_db)
    yield c
    c.close()
