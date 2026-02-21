# ukgeolocate

Give it a UK postcode and address, get back lat/lon coordinates.

Resolves UK addresses to coordinates by matching against local EPC and Ordnance Survey databases. No external API calls. Everything runs locally against two SQLite files.

## Prerequisites

This library requires two SQLite databases to function. Without them, nothing works.

| Database | File | Expected table | Description |
|---|---|---|---|
| EPC addresses | `EPClocations.db` | `epc_addresses` | Address records indexed by postcode, with UPRNs |
| OS Open UPRN | `OSOpenUPRN.db` | `uprns` | UPRN-to-coordinate mapping from Ordnance Survey |

> **TODO:** Database download links and preparation steps will be added here once the files are hosted. For now, ask the team for copies of `EPClocations.db` and `OSOpenUPRN.db`.

The library finds database files via environment variables, falling back to the current directory:

```bash
export EPCLOCATIONS_DB="/path/to/EPClocations.db"
export OSOPENUPRN_DB="/path/to/OSOpenUPRN.db"
```

## Installation

```bash
pip install -e .
```

No external dependencies. Python 3.9+ and the standard library only.

## Quick start

```python
from ukgeolocate import UKGeolocate

with UKGeolocate(epc_db="EPClocations.db", os_db="OSOpenUPRN.db") as client:
    result = client.find_coordinates("SW1A 2AA", "10 Downing Street, London")
    print(f"{result.latitude}, {result.longitude}")  # 51.5034, -0.1276
```

## CLI

Single lookup:

```bash
ukgeolocate "SW1A 2AA" "10 Downing Street"
```

Interactive mode (no arguments):

```bash
ukgeolocate
```

The CLI reads database paths from `EPCLOCATIONS_DB` and `OSOPENUPRN_DB` environment variables, or looks for the files in the current directory.

## Error handling

| Exception | When it's raised | What to do |
|---|---|---|
| `PostcodeInvalid` | Postcode fails UK format validation | Check the input. Must be a valid UK postcode like `SW1A 2AA`. |
| `NoMatchFound` | No address scores above the match threshold, or the matched UPRN has no coordinates in the OS database | Verify the address exists at that postcode. Consider lowering `match_threshold`. |
| `DatabaseNotFound` | A database file doesn't exist at the given path (including if deleted mid-session) | Check file paths and that the databases are in place. |
| `DatabaseInvalid` | A database exists but is missing expected tables (`epc_addresses` or `uprns`) | The database file is corrupt or the wrong file. Re-download. |

All exceptions inherit from `UKGeolocateError`, so you can catch that as a blanket handler:

```python
from ukgeolocate import UKGeolocateError

try:
    result = client.find_coordinates("SW1A 2AA", "10 Downing Street")
except UKGeolocateError as e:
    print(f"Lookup failed: {e}")
```

## API reference

### `UKGeolocate(epc_db, os_db, match_threshold=0.45)`

Main client. Opens connections to both databases on init.

| Parameter | Type | Description |
|---|---|---|
| `epc_db` | `str \| Path` | Path to the EPC addresses database |
| `os_db` | `str \| Path` | Path to the OS Open UPRN database |
| `match_threshold` | `float` | Minimum similarity score to accept a match (default `0.45`) |

Supports context manager usage (`with UKGeolocate(...) as client:`).

### `client.find_coordinates(postcode_raw, address_line) -> LookupResult`

Look up coordinates for a UK address.

| Parameter | Type | Description |
|---|---|---|
| `postcode_raw` | `str` | UK postcode in any format (`"SW1A2AA"`, `"sw1a 2aa"`, etc.) |
| `address_line` | `str` | Address to match against EPC records |

Raises `PostcodeInvalid`, `NoMatchFound`, or `DatabaseNotFound`.

### `client.health_check() -> dict`

Verify both databases are accessible and contain the expected tables. Never raises. Returns:

```python
{"healthy": True, "epc_db": "ok", "os_db": "ok"}           # all good
{"healthy": False, "epc_db": "ok", "os_db": "error msg"}    # OS DB problem
```

### `client.close()`

Explicitly close database connections. Called automatically when using the context manager.

### `LookupResult`

Frozen dataclass returned by `find_coordinates`.

| Field | Type | Description |
|---|---|---|
| `uprn` | `int` | Unique Property Reference Number |
| `matched_address` | `str` | The address string from the database that was matched |
| `match_score` | `float` | Similarity confidence between 0.0 and 1.0 |
| `easting` | `float` | OS National Grid easting |
| `northing` | `float` | OS National Grid northing |
| `latitude` | `float` | WGS84 latitude |
| `longitude` | `float` | WGS84 longitude |

Call `result.to_dict()` to get a plain dictionary (with `match_score` rounded to 3 decimal places).

## Match threshold

The `match_threshold` parameter (default `0.45`) controls how similar an address must be to count as a match. It uses Python's `difflib.SequenceMatcher` under the hood, scoring from 0.0 (completely different) to 1.0 (identical).

- **Lower values** (e.g. `0.3`): accept looser matches. More results, but higher risk of false positives.
- **Higher values** (e.g. `0.7`): require closer matches. Fewer false positives, but more `NoMatchFound` errors for slightly misspelled or abbreviated addresses.

The default of `0.45` works well for most real-world UK address inputs where formatting varies (commas, abbreviations, flat numbers in different positions).

## Limitations

- **UK only.** Does not geocode international addresses.
- **Offline only.** Requires local SQLite databases. No external API calls.
- **No fuzzy postcode matching.** The postcode must be valid and exact. Only the address line is fuzzy-matched.
