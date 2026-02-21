"""Tests for ukgeolocate.address module."""

from ukgeolocate.address import normalise, similarity


class TestNormalise:
    def test_uppercases(self):
        assert normalise("hello world") == "HELLO WORLD"

    def test_strips_commas(self):
        assert normalise("10, Downing Street, London") == "10 DOWNING STREET LONDON"

    def test_collapses_whitespace(self):
        assert normalise("  10   Downing   Street  ") == "10 DOWNING STREET"

    def test_combined(self):
        assert normalise("  flat a, 1 example road,  london  ") == "FLAT A 1 EXAMPLE ROAD LONDON"


class TestSimilarity:
    def test_identical_strings(self):
        assert similarity("10 Downing Street", "10 Downing Street") == 1.0

    def test_case_insensitive(self):
        assert similarity("10 downing street", "10 DOWNING STREET") == 1.0

    def test_comma_tolerance(self):
        score = similarity("10, Downing Street, London", "10 Downing Street London")
        assert score > 0.9

    def test_similar_addresses(self):
        score = similarity("10 DOWNING STREET LONDON", "10 DOWNING ST LONDON")
        assert score > 0.5

    def test_completely_different(self):
        score = similarity("10 DOWNING STREET", "99 BUCKINGHAM PALACE ROAD")
        assert score < 0.4
