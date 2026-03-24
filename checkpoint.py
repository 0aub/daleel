"""Checkpoint save/load for resuming interrupted scrapes.

Stores progress as JSON so scrapes can be resumed after interruption.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime

__all__ = ["CheckpointData", "save_checkpoint", "load_checkpoint", "find_latest_checkpoint"]

logger = logging.getLogger(__name__)


@dataclass
class CheckpointData:
    """Serializable checkpoint state."""

    region_key: str
    target: int
    started_at: str
    last_updated: str
    completed_tasks: list[dict] = field(default_factory=list)
    raw_count: int = 0
    unique_count: int = 0
    api_calls_made: int = 0
    seen_place_ids: list[str] = field(default_factory=list)
    results_file: str = ""


def save_checkpoint(data: CheckpointData, checkpoint_dir: str = "data/checkpoints") -> str:
    """Save checkpoint to JSON file. Returns the file path."""
    os.makedirs(checkpoint_dir, exist_ok=True)
    path = os.path.join(checkpoint_dir, f"{data.region_key}_checkpoint.json")
    data.last_updated = datetime.now(UTC).isoformat()

    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "region": data.region_key,
            "target": data.target,
            "started_at": data.started_at,
            "last_updated": data.last_updated,
            "completed_tasks": data.completed_tasks,
            "raw_count": data.raw_count,
            "unique_count": data.unique_count,
            "api_calls_made": data.api_calls_made,
            "seen_place_ids": data.seen_place_ids,
            "results_file": data.results_file,
        }, f, ensure_ascii=False, indent=2)

    logger.debug("Checkpoint saved: %s", path)
    return path


def load_checkpoint(path: str) -> CheckpointData:
    """Load checkpoint from JSON file."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    return CheckpointData(
        region_key=raw["region"],
        target=raw["target"],
        started_at=raw["started_at"],
        last_updated=raw["last_updated"],
        completed_tasks=raw.get("completed_tasks", []),
        raw_count=raw.get("raw_count", 0),
        unique_count=raw.get("unique_count", 0),
        api_calls_made=raw.get("api_calls_made", 0),
        seen_place_ids=raw.get("seen_place_ids", []),
        results_file=raw.get("results_file", ""),
    )


def find_latest_checkpoint(checkpoint_dir: str = "data/checkpoints") -> str | None:
    """Find the most recently updated checkpoint file, or None."""
    if not os.path.isdir(checkpoint_dir):
        return None

    checkpoints = [
        os.path.join(checkpoint_dir, f)
        for f in os.listdir(checkpoint_dir)
        if f.endswith("_checkpoint.json")
    ]
    if not checkpoints:
        return None

    return max(checkpoints, key=os.path.getmtime)
