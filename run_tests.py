"""
Minimal test runner using only the standard library.
Run: python3 run_tests.py
"""

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to path so ukgeolocate is importable
sys.path.insert(0, str(Path(__file__).parent / "src"))


def make_epc_db(directory: str) -> Path:
    """Create a small EPC database with test rows."""
    db_path = Path(directory) / "test_epc.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE epc_addresses ("
        "lmk_key TEXT PRIMARY KEY, postcode TEXT, "
        "address1 TEXT, address2 TEXT, address3 TEXT, "
        "address TEXT, uprn TEXT)"
    )
    conn.execute("CREATE INDEX idx_epc_postcode ON epc_addresses (postcode)")
    rows = [
        ("lmk001", "SW1A 2AA", "10 DOWNING STREET", "", "",
         "10, DOWNING STREET, LONDON", "100023336956"),
        ("lmk002", "SW1A 2AA", "11 DOWNING STREET", "", "",
         "11, DOWNING STREET, LONDON", "100023336957"),
        ("lmk003", "EC1A 1BB", "1 EXAMPLE ROAD", "FLAT A", "",
         "FLAT A, 1 EXAMPLE ROAD, LONDON", "200000000001"),
        ("lmk004", "M1 1AE", "50 HIGH STREET", "", "",
         "50, HIGH STREET, MANCHESTER", "300000000001"),
        ("lmk005", "SW1A 2AA", "12 DOWNING STREET", "", "",
         "12, DOWNING STREET, LONDON", "not_a_number"),
    ]
    conn.executemany("INSERT INTO epc_addresses VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return db_path


def make_os_db(directory: str) -> Path:
    """Create a small OS UPRN database with matching coordinates."""
    db_path = Path(directory) / "test_os.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE uprns ("
        "UPRN INTEGER PRIMARY KEY, X_COORDINATE REAL, "
        "Y_COORDINATE REAL, LATITUDE REAL, LONGITUDE REAL)"
    )
    rows = [
        (100023336956, 530047.0, 179951.0, 51.5034, -0.1276),
        (100023336957, 530048.0, 179952.0, 51.5035, -0.1275),
        (200000000001, 532000.0, 181000.0, 51.5200, -0.1000),
        (300000000001, 383800.0, 398000.0, 53.4808, -2.2426),
    ]
    conn.executemany("INSERT INTO uprns VALUES (?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return db_path


# ── Postcode Tests ────────────────────────────────────────────

class TestPostcodeValidate(unittest.TestCase):
    def test_valid(self):
        from ukgeolocate.postcode import validate
        for pc in ["SW1A 2AA", "EC1A 1BB", "W1A 0AX", "M1 1AE", "sw1a2aa"]:
            self.assertTrue(validate(pc), f"Expected valid: {pc}")

    def test_invalid(self):
        from ukgeolocate.postcode import validate
        for pc in ["12345", "ABCDE", "", "75001", "INVALID"]:
            self.assertFalse(validate(pc), f"Expected invalid: {pc}")


class TestPostcodeNormalise(unittest.TestCase):
    def test_formats(self):
        from ukgeolocate.postcode import normalise
        self.assertEqual(normalise("sw1a2aa"), "SW1A 2AA")
        self.assertEqual(normalise("  EC1A1BB  "), "EC1A 1BB")
        self.assertEqual(normalise("m1 1ae"), "M1 1AE")

    def test_raises_on_invalid(self):
        from ukgeolocate.postcode import normalise
        from ukgeolocate.exceptions import PostcodeInvalid
        with self.assertRaises(PostcodeInvalid):
            normalise("INVALID")


# ── Address Tests ─────────────────────────────────────────────

class TestAddressNormalise(unittest.TestCase):
    def test_uppercases(self):
        from ukgeolocate.address import normalise
        self.assertEqual(normalise("hello world"), "HELLO WORLD")

    def test_strips_commas(self):
        from ukgeolocate.address import normalise
        self.assertEqual(
            normalise("10, Downing Street, London"),
            "10 DOWNING STREET LONDON",
        )

    def test_collapses_whitespace(self):
        from ukgeolocate.address import normalise
        self.assertEqual(normalise("  10   Downing  "), "10 DOWNING")


class TestAddressSimilarity(unittest.TestCase):
    def test_identical(self):
        from ukgeolocate.address import similarity
        self.assertEqual(similarity("10 Downing", "10 Downing"), 1.0)

    def test_case_insensitive(self):
        from ukgeolocate.address import similarity
        self.assertEqual(similarity("10 downing", "10 DOWNING"), 1.0)

    def test_different(self):
        from ukgeolocate.address import similarity
        score = similarity("10 DOWNING", "99 BUCKINGHAM PALACE")
        self.assertLess(score, 0.4)


# ── Client Tests ──────────────────────────────────────────────

class TestClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.mkdtemp()
        cls.epc_db = make_epc_db(cls._tmpdir)
        cls.os_db = make_os_db(cls._tmpdir)

    def _make_client(self):
        from ukgeolocate import UKGeolocate
        return UKGeolocate(epc_db=self.epc_db, os_db=self.os_db)

    def test_successful_lookup(self):
        from ukgeolocate.models import LookupResult
        client = self._make_client()
        result = client.find_coordinates("SW1A 2AA", "10 Downing Street")
        self.assertIsInstance(result, LookupResult)
        self.assertEqual(result.uprn, 100023336956)
        self.assertEqual(result.latitude, 51.5034)
        self.assertEqual(result.longitude, -0.1276)
        self.assertGreater(result.match_score, 0.5)
        client.close()

    def test_different_postcode(self):
        client = self._make_client()
        result = client.find_coordinates("M1 1AE", "50 High Street")
        self.assertEqual(result.uprn, 300000000001)
        self.assertEqual(result.latitude, 53.4808)
        client.close()

    def test_invalid_postcode_raises(self):
        from ukgeolocate.exceptions import PostcodeInvalid
        client = self._make_client()
        with self.assertRaises(PostcodeInvalid):
            client.find_coordinates("INVALID", "10 Downing Street")
        client.close()

    def test_no_match_raises(self):
        from ukgeolocate.exceptions import NoMatchFound
        client = self._make_client()
        with self.assertRaises(NoMatchFound):
            client.find_coordinates("SW1A 2AA", "ZZZZZ COMPLETELY UNRELATED XYZZY")
        client.close()

    def test_bad_uprn_row_skipped(self):
        client = self._make_client()
        # lmk005 has uprn="not_a_number" — should be skipped
        result = client.find_coordinates("SW1A 2AA", "10 Downing Street")
        self.assertEqual(result.uprn, 100023336956)
        client.close()

    def test_health_check(self):
        client = self._make_client()
        status = client.health_check()
        self.assertTrue(status["healthy"])
        self.assertEqual(status["epc_db"], "ok")
        self.assertEqual(status["os_db"], "ok")
        client.close()

    def test_context_manager(self):
        from ukgeolocate import UKGeolocate
        with UKGeolocate(epc_db=self.epc_db, os_db=self.os_db) as c:
            result = c.find_coordinates("SW1A 2AA", "10 Downing Street")
            self.assertEqual(result.uprn, 100023336956)
        # Pools should be closed
        self.assertIsNone(c._epc_pool._conn)
        self.assertIsNone(c._os_pool._conn)

    def test_to_dict(self):
        client = self._make_client()
        result = client.find_coordinates("SW1A 2AA", "10 Downing Street")
        d = result.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["uprn"], 100023336956)
        expected_keys = {
            "uprn", "matched_address", "match_score",
            "easting", "northing", "latitude", "longitude",
        }
        self.assertEqual(set(d.keys()), expected_keys)
        client.close()


class TestDatabaseNotFound(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.mkdtemp()
        cls.epc_db = make_epc_db(cls._tmpdir)
        cls.os_db = make_os_db(cls._tmpdir)

    def test_missing_epc_db(self):
        from ukgeolocate import UKGeolocate
        from ukgeolocate.exceptions import DatabaseNotFound
        with self.assertRaises(DatabaseNotFound) as ctx:
            UKGeolocate(epc_db="/nonexistent/path.db", os_db=self.os_db)
        self.assertEqual(ctx.exception.db_name, "EPC")

    def test_missing_os_db(self):
        from ukgeolocate import UKGeolocate
        from ukgeolocate.exceptions import DatabaseNotFound
        with self.assertRaises(DatabaseNotFound) as ctx:
            UKGeolocate(epc_db=self.epc_db, os_db="/nonexistent/path.db")
        self.assertEqual(ctx.exception.db_name, "OS Open UPRN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
