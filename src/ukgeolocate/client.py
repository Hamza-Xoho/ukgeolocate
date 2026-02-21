"""UKGeolocate client — the main entry point for the library."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ukgeolocate import address, postcode
from ukgeolocate._db import _DatabasePool
from ukgeolocate.exceptions import NoMatchFound
from ukgeolocate.models import LookupResult

_DEFAULT_THRESHOLD = 0.45


class UKGeolocate:
    """
    UPRN-based UK address-to-coordinate resolver.

    Initialise with paths to the two required SQLite databases.
    Validates that both databases exist and contain the expected
    tables on construction.
    """

    def __init__(
        self,
        epc_db: str | Path,
        os_db: str | Path,
        match_threshold: float = _DEFAULT_THRESHOLD,
    ):
        self._threshold = match_threshold
        self._epc_pool = _DatabasePool(Path(epc_db), "EPC")
        self._os_pool = _DatabasePool(Path(os_db), "OS Open UPRN")
        self._validate_databases()

    # ── Public API ────────────────────────────────────────────────

    def find_coordinates(
        self, postcode_raw: str, address_line: str
    ) -> LookupResult:
        """
        Resolve a UK postcode and address to coordinates.

        Returns a LookupResult on success.
        Raises PostcodeInvalid, NoMatchFound, or DatabaseNotFound on failure.
        """
        pc = postcode.normalise(postcode_raw)

        uprn, matched_address, score = self._lookup_uprn(pc, address_line)
        x, y, lat, lon = self._lookup_coordinates(uprn, pc, address_line)

        return LookupResult(
            uprn=uprn,
            matched_address=matched_address,
            match_score=score,
            easting=x,
            northing=y,
            latitude=lat,
            longitude=lon,
        )

    def health_check(self) -> dict:
        """
        Verify both databases are accessible and contain expected tables.

        Returns a dict with status information.
        """
        status: dict = {"healthy": True, "epc_db": "ok", "os_db": "ok"}
        try:
            self._epc_pool.validate_tables(["epc_addresses"])
        except Exception as exc:
            status["healthy"] = False
            status["epc_db"] = str(exc)
        try:
            self._os_pool.validate_tables(["uprns"])
        except Exception as exc:
            status["healthy"] = False
            status["os_db"] = str(exc)
        return status

    def close(self) -> None:
        """Close both database connection pools."""
        self._epc_pool.close()
        self._os_pool.close()

    def __enter__(self) -> UKGeolocate:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ── Private helpers ───────────────────────────────────────────

    def _validate_databases(self) -> None:
        """Check both DB files exist and have the expected tables."""
        self._epc_pool.validate_tables(["epc_addresses"])
        self._os_pool.validate_tables(["uprns"])

    def _lookup_uprn(
        self, norm_postcode: str, address_line: str
    ) -> tuple[int, str, float]:
        """
        Search the EPC database for the best UPRN matching *norm_postcode*
        and *address_line*.

        Returns (uprn, matched_address, score).
        Raises NoMatchFound if no candidate exceeds the threshold.
        """
        norm_query = address.normalise(address_line)

        cur = self._epc_pool.execute(
            "SELECT uprn, address1, address2, address3, address "
            "FROM epc_addresses "
            "WHERE postcode = ? AND uprn IS NOT NULL AND uprn != ''",
            (norm_postcode,),
        )

        best: Optional[tuple[int, str, float]] = None

        for uprn_str, addr1, addr2, addr3, addr_full in cur:
            # Score against every address column; keep the highest
            row_score = max(
                address.similarity(addr1 or "", norm_query),
                address.similarity(addr2 or "", norm_query),
                address.similarity(addr3 or "", norm_query),
                address.similarity(addr_full or "", norm_query),
            )
            if row_score >= self._threshold and (
                best is None or row_score > best[2]
            ):
                try:
                    uprn_int = int(uprn_str)
                except (ValueError, TypeError):
                    continue
                best = (
                    uprn_int,
                    addr_full or addr1 or "",
                    row_score,
                )
                # Perfect match — no need to keep scanning
                if row_score == 1.0:
                    break

        if best is None:
            raise NoMatchFound(norm_postcode, address_line)
        return best

    def _lookup_coordinates(
        self, uprn: int, postcode_for_error: str, address_for_error: str
    ) -> tuple[float, float, float, float]:
        """
        Return (easting, northing, latitude, longitude) for the given UPRN.

        Raises NoMatchFound if the UPRN is not in the OS database.
        """
        cur = self._os_pool.execute(
            "SELECT X_COORDINATE, Y_COORDINATE, LATITUDE, LONGITUDE "
            "FROM uprns WHERE UPRN = ?",
            (uprn,),
        )
        row = cur.fetchone()
        if row is None:
            raise NoMatchFound(postcode_for_error, address_for_error)
        return (row[0], row[1], row[2], row[3])
