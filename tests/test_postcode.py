"""Tests for ukgeolocate.postcode module."""

import pytest

from ukgeolocate.exceptions import PostcodeInvalid
from ukgeolocate.postcode import normalise, validate


class TestValidate:
    @pytest.mark.parametrize(
        "pc",
        ["SW1A 2AA", "EC1A 1BB", "W1A 0AX", "M1 1AE", "B33 8TH", "CR2 6XH"],
    )
    def test_valid_postcodes(self, pc: str):
        assert validate(pc) is True

    @pytest.mark.parametrize(
        "pc",
        ["sw1a2aa", "  EC1A 1BB  ", "m11ae"],
    )
    def test_valid_postcodes_flexible_input(self, pc: str):
        assert validate(pc) is True

    @pytest.mark.parametrize(
        "pc",
        ["12345", "ABCDE", "", "75001", "INVALID", "123 ABC"],
    )
    def test_invalid_postcodes(self, pc: str):
        assert validate(pc) is False


class TestNormalise:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("sw1a2aa", "SW1A 2AA"),
            ("  EC1A1BB  ", "EC1A 1BB"),
            ("m1 1ae", "M1 1AE"),
            ("W1A 0AX", "W1A 0AX"),
        ],
    )
    def test_normalise_formats_correctly(self, raw: str, expected: str):
        assert normalise(raw) == expected

    @pytest.mark.parametrize("bad", ["12345", "", "INVALID", "75001"])
    def test_normalise_raises_on_invalid(self, bad: str):
        with pytest.raises(PostcodeInvalid) as exc_info:
            normalise(bad)
        assert exc_info.value.postcode == bad
