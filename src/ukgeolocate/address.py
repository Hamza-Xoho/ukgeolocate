"""Address normalisation and similarity scoring."""

from difflib import SequenceMatcher


def normalise(raw: str) -> str:
    """Upper-case, strip commas and collapse whitespace."""
    return " ".join(raw.upper().replace(",", "").split())


def similarity(candidate: str, query: str) -> float:
    """
    Score how well *candidate* (from the DB) matches the user *query*.

    Uses SequenceMatcher ratio (0.0-1.0) on normalised forms so that
    minor differences (extra commas, different spacing) are tolerated.
    """
    a = normalise(candidate)
    b = normalise(query)
    return SequenceMatcher(None, a, b).ratio()
