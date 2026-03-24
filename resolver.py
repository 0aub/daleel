"""Fuzzy region/city name resolver.

Handles Arabic names, English names, common misspellings, and case-insensitive matching.
"""

from dataclasses import dataclass

from regions import REGIONS

__all__ = ["ResolvedTarget", "resolve_input"]


@dataclass
class ResolvedTarget:
    """A resolved scraping target — either a full region or a specific city."""

    region_key: str
    region_name: str
    city_names: list[str]  # empty = all cities in region


def resolve_input(user_input: str) -> list[ResolvedTarget]:
    """Resolve user input into a list of scraping targets.

    Supports:
    - Exact region name: "Riyadh Region"
    - Short region name: "Riyadh"
    - City name: "Buraidah" → Qaseem Region (only Buraidah)
    - Arabic name: "الرياض"
    - Comma-separated: "Riyadh,Jeddah"
    - "all" → every region
    """
    if user_input.strip().lower() == "all":
        return [
            ResolvedTarget(
                region_key=key,
                region_name=region["name_en"],
                city_names=[],
            )
            for key, region in REGIONS.items()
        ]

    targets = []
    for part in user_input.split(","):
        part = part.strip()
        if not part:
            continue
        target = _resolve_single(part)
        if target is None:
            raise ValueError(
                f"Could not resolve '{part}'. Use --list-regions to see available options."
            )
        targets.append(target)

    return targets


def _resolve_single(name: str) -> ResolvedTarget | None:
    """Resolve a single region or city name."""
    normalized = name.strip().lower()

    # Try matching against regions first
    for key, region in REGIONS.items():
        if normalized in (region["name_en"].lower(), key.lower()):
            return ResolvedTarget(region_key=key, region_name=region["name_en"], city_names=[])
        if normalized in [a.lower() for a in region["aliases"]]:
            return ResolvedTarget(region_key=key, region_name=region["name_en"], city_names=[])

    # Try matching against cities
    for key, region in REGIONS.items():
        for city_name, city in region["cities"].items():
            if normalized in (city_name.lower(), city["name_ar"]):
                return ResolvedTarget(
                    region_key=key,
                    region_name=region["name_en"],
                    city_names=[city_name],
                )
            if normalized in [a.lower() for a in city["aliases"]]:
                return ResolvedTarget(
                    region_key=key,
                    region_name=region["name_en"],
                    city_names=[city_name],
                )

    return None
