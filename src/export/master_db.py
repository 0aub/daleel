"""Persistent master database of all seen place IDs across runs.

Ensures businesses scraped in previous runs are not duplicated in new runs.
Stored as a simple JSON file at data/master_place_ids.json.
"""

import json
import logging
import os

__all__ = ["MasterDB"]

logger = logging.getLogger(__name__)

DEFAULT_PATH = "data/master_place_ids.json"


class MasterDB:
    """Persistent set of all place IDs ever scraped."""

    def __init__(self, path: str = DEFAULT_PATH) -> None:
        self._path = path
        self._ids: set[str] = set()
        self._new_count = 0
        self._load()

    def _load(self) -> None:
        """Load existing IDs from disk."""
        if not os.path.exists(self._path):
            logger.info("No master DB found at %s — starting fresh", self._path)
            return
        with open(self._path, encoding="utf-8") as f:
            data = json.load(f)
        self._ids = set(data.get("place_ids", []))
        logger.info("Loaded master DB: %d existing place IDs", len(self._ids))

    def save(self) -> None:
        """Persist current IDs to disk."""
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump({
                "count": len(self._ids),
                "place_ids": sorted(self._ids),
            }, f, ensure_ascii=False)
        logger.info("Master DB saved: %d total IDs (%d new this run)",
                     len(self._ids), self._new_count)

    def contains(self, place_id: str) -> bool:
        """Check if a place ID exists in the master database."""
        return place_id in self._ids

    def add(self, place_id: str) -> bool:
        """Add a place ID. Returns True if new, False if already existed."""
        if place_id in self._ids:
            return False
        self._ids.add(place_id)
        self._new_count += 1
        return True

    @property
    def total_count(self) -> int:
        """Total unique place IDs across all runs."""
        return len(self._ids)

    @property
    def new_count(self) -> int:
        """New place IDs added in this run."""
        return self._new_count

    @property
    def ids(self) -> set[str]:
        """All place IDs."""
        return set(self._ids)
