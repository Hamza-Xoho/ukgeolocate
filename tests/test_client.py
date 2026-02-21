"""Tests for ukgeolocate.client module."""

from pathlib import Path

import pytest

from ukgeolocate import UKGeolocate
from ukgeolocate.exceptions import (
    DatabaseNotFound,
    NoMatchFound,
    PostcodeInvalid,
)
from ukgeolocate.models import LookupResult


class TestFindCoordinates:
    def test_successful_lookup(self, client: UKGeolocate):
        result = client.find_coordinates("SW1A 2AA", "10 Downing Street")
        assert isinstance(result, LookupResult)
        assert result.uprn == 100023336956
        assert result.latitude == 51.5034
        assert result.longitude == -0.1276
        assert result.easting == 530047.0
        assert result.northing == 179951.0
        assert result.match_score > 0.5

    def test_matched_address_populated(self, client: UKGeolocate):
        result = client.find_coordinates("SW1A 2AA", "10 Downing Street")
        assert "DOWNING" in result.matched_address.upper()

    def test_different_postcode(self, client: UKGeolocate):
        result = client.find_coordinates("M1 1AE", "50 High Street")
        assert result.uprn == 300000000001
        assert result.latitude == 53.4808

    def test_invalid_postcode_raises(self, client: UKGeolocate):
        with pytest.raises(PostcodeInvalid):
            client.find_coordinates("INVALID", "10 Downing Street")

    def test_no_match_raises(self, client: UKGeolocate):
        with pytest.raises(NoMatchFound):
            client.find_coordinates("SW1A 2AA", "ZZZZZ COMPLETELY UNRELATED XYZZY")

    def test_bad_uprn_row_skipped(self, client: UKGeolocate):
        # lmk005 has uprn="not_a_number" — should be skipped, not crash
        result = client.find_coordinates("SW1A 2AA", "10 Downing Street")
        assert result.uprn == 100023336956


class TestHealthCheck:
    def test_healthy(self, client: UKGeolocate):
        status = client.health_check()
        assert status["healthy"] is True
        assert status["epc_db"] == "ok"
        assert status["os_db"] == "ok"

    def test_unhealthy_missing_db(self, tmp_path: Path):
        # Create only the OS db (valid), EPC path is bogus
        import sqlite3

        os_db = tmp_path / "os.db"
        conn = sqlite3.connect(str(os_db))
        conn.execute(
            "CREATE TABLE uprns (UPRN INTEGER PRIMARY KEY, "
            "X_COORDINATE REAL, Y_COORDINATE REAL, "
            "LATITUDE REAL, LONGITUDE REAL)"
        )
        conn.commit()
        conn.close()

        with pytest.raises(DatabaseNotFound):
            UKGeolocate(
                epc_db=tmp_path / "nonexistent.db", os_db=os_db
            )


class TestContextManager:
    def test_context_manager_closes(self, tmp_epc_db: Path, tmp_os_db: Path):
        with UKGeolocate(epc_db=tmp_epc_db, os_db=tmp_os_db) as c:
            result = c.find_coordinates("SW1A 2AA", "10 Downing Street")
            assert result.uprn == 100023336956
        # After exiting, pools should be closed
        assert c._epc_pool._conn is None
        assert c._os_pool._conn is None


class TestDatabaseNotFound:
    def test_missing_epc_db(self, tmp_os_db: Path):
        with pytest.raises(DatabaseNotFound) as exc_info:
            UKGeolocate(epc_db="/nonexistent/path.db", os_db=tmp_os_db)
        assert exc_info.value.db_name == "EPC"

    def test_missing_os_db(self, tmp_epc_db: Path):
        with pytest.raises(DatabaseNotFound) as exc_info:
            UKGeolocate(epc_db=tmp_epc_db, os_db="/nonexistent/path.db")
        assert exc_info.value.db_name == "OS Open UPRN"


class TestLookupResultToDict:
    def test_to_dict(self, client: UKGeolocate):
        result = client.find_coordinates("SW1A 2AA", "10 Downing Street")
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["uprn"] == 100023336956
        assert d["latitude"] == 51.5034
        assert d["longitude"] == -0.1276
        assert isinstance(d["match_score"], float)

    def test_to_dict_keys(self, client: UKGeolocate):
        result = client.find_coordinates("SW1A 2AA", "10 Downing Street")
        expected_keys = {
            "uprn",
            "matched_address",
            "match_score",
            "easting",
            "northing",
            "latitude",
            "longitude",
        }
        assert set(result.to_dict().keys()) == expected_keys
