"""Deduplication by Google Place ID.

Tracks seen place IDs to ensure each business appears only once in the output.
"""

from core.searcher import Place

__all__ = ["Deduplicator"]


class Deduplicator:
    """Tracks unique places by their Google place_id."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def is_duplicate(self, place_id: str) -> bool:
        """Check if a place_id has already been seen."""
        return place_id in self._seen

    def add(self, place: Place) -> bool:
        """Add a place if not already seen. Returns True if new, False if duplicate."""
        if place.place_id in self._seen:
            return False
        self._seen.add(place.place_id)
        return True

    def add_batch(self, places: list[Place]) -> list[Place]:
        """Add multiple places, returning only the new (non-duplicate) ones."""
        new_places = []
        for place in places:
            if self.add(place):
                new_places.append(place)
        return new_places

    @property
    def count(self) -> int:
        """Number of unique places seen."""
        return len(self._seen)

    @property
    def seen_ids(self) -> set[str]:
        """All seen place IDs (for checkpoint serialization)."""
        return set(self._seen)

    def load_ids(self, place_ids: set[str]) -> None:
        """Load previously seen IDs (for checkpoint resume)."""
        self._seen.update(place_ids)
