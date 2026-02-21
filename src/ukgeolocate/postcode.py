"""UK postcode validation and normalisation."""

import re

from ukgeolocate.exceptions import PostcodeInvalid

_UK_POSTCODE_RE = re.compile(
    r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$",
    re.IGNORECASE,
)


def validate(raw: str) -> bool:
    """Return True if *raw* looks like a valid UK postcode."""
    return bool(_UK_POSTCODE_RE.match(raw.strip()))


def normalise(raw: str) -> str:
    """
    Normalise to the canonical 'AREA NNN' format, e.g. 'sw1a2aa' -> 'SW1A 2AA'.

    Raises PostcodeInvalid if the input is not a valid UK postcode.
    """
    if not validate(raw):
        raise PostcodeInvalid(raw)
    stripped = raw.strip().upper().replace(" ", "")
    return f"{stripped[:-3]} {stripped[-3:]}"
