"""Custom exception hierarchy for ukgeolocate."""


class UKGeolocateError(Exception):
    """Base exception for all ukgeolocate errors."""


class PostcodeInvalid(UKGeolocateError):
    """The provided string is not a valid UK postcode."""

    def __init__(self, postcode: str):
        self.postcode = postcode
        super().__init__(f"Invalid UK postcode: '{postcode}'")


class DatabaseNotFound(UKGeolocateError):
    """A required SQLite database file does not exist."""

    def __init__(self, path: str, db_name: str):
        self.path = path
        self.db_name = db_name
        super().__init__(f"{db_name} database not found at: {path}")


class DatabaseInvalid(UKGeolocateError):
    """A database exists but is missing expected tables or columns."""

    def __init__(self, path: str, detail: str):
        self.path = path
        super().__init__(f"Invalid database at {path}: {detail}")


class NoMatchFound(UKGeolocateError):
    """No UPRN or coordinate match was found."""

    def __init__(self, postcode: str, address: str):
        self.postcode = postcode
        self.address = address
        super().__init__(f"No match found for '{address}' at '{postcode}'")
