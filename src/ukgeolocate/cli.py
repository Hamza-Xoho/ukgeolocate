"""
UPRN Coordinate Lookup — Interactive CLI
=========================================
Thin wrapper around the ukgeolocate library.

Usage:
    ukgeolocate                          # interactive mode
    ukgeolocate "SW1A 2AA" "10 Downing"  # single lookup

Database paths are read from environment variables:
    EPCLOCATIONS_DB   Path to EPClocations.db
    OSOPENUPRN_DB     Path to OSOpenUPRN.db

If not set, looks for the files in the current working directory.
"""

import os
import sys
from pathlib import Path

from ukgeolocate import UKGeolocate
from ukgeolocate.exceptions import (
    DatabaseNotFound,
    NoMatchFound,
    PostcodeInvalid,
    UKGeolocateError,
)
from ukgeolocate.postcode import validate

# ── Default database paths ────────────────────────────────────
# Environment variables take priority. Fall back to CWD, which is
# stable regardless of where the package is installed.
_DEFAULT_EPC = os.environ.get(
    "EPCLOCATIONS_DB", str(Path.cwd() / "EPClocations.db")
)
_DEFAULT_OS = os.environ.get(
    "OSOPENUPRN_DB", str(Path.cwd() / "OSOpenUPRN.db")
)

_BANNER = """\
╔══════════════════════════════════════╗
║       UPRN Coordinate Lookup         ║
║  Postcode + Address → Coordinates    ║
╚══════════════════════════════════════╝
Type 'q' to quit.
"""


def _run_interactive(client: UKGeolocate) -> None:
    print(_BANNER)

    while True:
        # -- Postcode ---------------------------------------------------
        try:
            raw_postcode = input("\nPostcode:        ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if raw_postcode.lower() in ("q", "quit", "exit"):
            print("Bye!")
            break
        if not raw_postcode:
            print("  ✗ Postcode is required.")
            continue
        if not validate(raw_postcode):
            print(f"  ✗ Invalid UK postcode format: '{raw_postcode}'")
            continue

        # -- Address ----------------------------------------------------
        try:
            raw_address = input("Address line 1:  ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not raw_address:
            print("  ✗ Address line 1 is required.")
            continue

        # -- Lookup -----------------------------------------------------
        print("  ⏳ Searching EPC database …", end="", flush=True)
        try:
            result = client.find_coordinates(raw_postcode, raw_address)
        except NoMatchFound:
            print(
                f"\r  ✗ No matching UPRN for "
                f"'{raw_postcode}' / '{raw_address}'"
            )
            continue
        except UKGeolocateError as exc:
            print(f"\r  ✗ Error: {exc}")
            continue

        # -- Display ----------------------------------------------------
        confidence = f"{result.match_score:.0%}"
        print(f"\r  ✓ Match found ({confidence} confidence)")
        print()
        print(f"  ┌──────────────────────────────────────────────────────┐")
        print(f"  │  Matched Address   {result.matched_address:<35}│")
        print(f"  │  UPRN              {result.uprn:<35}│")
        print(f"  │  Easting           {result.easting:<35}│")
        print(f"  │  Northing          {result.northing:<35}│")
        print(f"  │  Latitude          {result.latitude:<35}│")
        print(f"  │  Longitude         {result.longitude:<35}│")
        print(f"  │  Match Confidence  {confidence:<35}│")
        print(f"  └──────────────────────────────────────────────────────┘")


def main() -> None:
    """Entry point — supports both CLI args and interactive mode."""
    try:
        client = UKGeolocate(epc_db=_DEFAULT_EPC, os_db=_DEFAULT_OS)
    except DatabaseNotFound as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(
            "Set EPCLOCATIONS_DB and OSOPENUPRN_DB environment variables, "
            "or run from the directory containing the databases.",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        if len(sys.argv) == 3:
            # Single-shot mode
            try:
                result = client.find_coordinates(sys.argv[1], sys.argv[2])
            except PostcodeInvalid as exc:
                print(f"Invalid postcode: {exc.postcode}", file=sys.stderr)
                sys.exit(1)
            except NoMatchFound:
                print("No match found.", file=sys.stderr)
                sys.exit(1)
            for key, val in result.to_dict().items():
                print(f"{key:>20}: {val}")
        else:
            _run_interactive(client)
    finally:
        client.close()


if __name__ == "__main__":
    main()
