"""Tests for the deduplicator."""

from core.dedup import Deduplicator
from core.searcher import Place


def _make_place(place_id: str, name: str = "Test") -> Place:
    """Helper to create a minimal Place for testing."""
    return Place(
        place_id=place_id, name=name, name_language="en", address="",
        latitude=0.0, longitude=0.0, types=[], primary_type="",
        primary_type_display="", phone_local="", phone_intl="",
        rating=None, review_count=0, website="", google_maps_url="",
        business_status="", hours="", region="", city="", query="",
    )


class TestDeduplicator:
    def test_add_new_returns_true(self):
        dedup = Deduplicator()
        assert dedup.add(_make_place("abc123")) is True

    def test_add_duplicate_returns_false(self):
        dedup = Deduplicator()
        dedup.add(_make_place("abc123"))
        assert dedup.add(_make_place("abc123")) is False

    def test_count(self):
        dedup = Deduplicator()
        dedup.add(_make_place("a"))
        dedup.add(_make_place("b"))
        dedup.add(_make_place("a"))  # duplicate
        assert dedup.count == 2

    def test_is_duplicate(self):
        dedup = Deduplicator()
        dedup.add(_make_place("abc"))
        assert dedup.is_duplicate("abc") is True
        assert dedup.is_duplicate("xyz") is False

    def test_add_batch(self):
        dedup = Deduplicator()
        places = [_make_place("a"), _make_place("b"), _make_place("a")]
        new = dedup.add_batch(places)
        assert len(new) == 2
        assert dedup.count == 2

    def test_load_ids(self):
        dedup = Deduplicator()
        dedup.load_ids({"x", "y"})
        assert dedup.is_duplicate("x") is True
        assert dedup.count == 2
