"""Dynamic scrape strategy planner.

Determines grid density and query depth based on target count,
starting from city centers and expanding outward.
"""

from dataclasses import dataclass, field

from core.grid import GridPoint, generate_grid
from models.queries import TIER_1_QUERIES, TIER_2_QUERIES, TIER_3_QUERIES

__all__ = ["ScrapeTask", "ScrapePlan", "create_plan"]


@dataclass
class ScrapeTask:
    """A single scraping task: one city, one set of grid points, one set of queries."""

    city_name: str
    grid_points: list[GridPoint]
    queries: list[str]

    @property
    def estimated_api_calls(self) -> int:
        return len(self.grid_points) * len(self.queries)


@dataclass
class ScrapePlan:
    """Full scraping plan with ordered tasks."""

    tasks: list[ScrapeTask] = field(default_factory=list)

    def add(self, city_name: str, grid_points: list[GridPoint], queries: list[str]) -> None:
        self.tasks.append(ScrapeTask(city_name=city_name, grid_points=grid_points, queries=queries))

    @property
    def total_api_calls(self) -> int:
        return sum(t.estimated_api_calls for t in self.tasks)

    @property
    def cities(self) -> list[str]:
        return list(dict.fromkeys(t.city_name for t in self.tasks))


def create_plan(
    region_profile: dict,
    target_count: int,
    city_filter: list[str] | None = None,
    avg_unique_per_call: int = 8,
) -> ScrapePlan:
    """Create a dynamic scraping plan based on target count.

    Strategy:
    - Start from city centers (highest commercial density)
    - Use concentric expansion: center first, then outward rings
    - Begin with Tier 1 queries (most results per query)
    - Add Tier 2 if needed, then Tier 3
    - Stop planning once estimated yield >= target * 1.2
    """
    plan = ScrapePlan()
    estimated_yield = 0

    cities = region_profile["cities"]
    if city_filter:
        cities = {k: v for k, v in cities.items() if k in city_filter}

    # Sort cities by population (largest first)
    cities_sorted = sorted(cities.items(), key=lambda x: x[1]["population"], reverse=True)

    for city_name, city_config in cities_sorted:
        if estimated_yield >= target_count * 1.2:
            break

        core_grid = generate_grid(
            city_config["bounds"],
            step_km=city_config["base_grid_step_km"],
            strategy="center_first",
        )

        # Phase 1: Core grid + Tier 1 queries
        tier1_yield = len(core_grid) * len(TIER_1_QUERIES) * avg_unique_per_call
        plan.add(city_name, core_grid, list(TIER_1_QUERIES))
        estimated_yield += tier1_yield

        if estimated_yield >= target_count * 1.2:
            break

        # Phase 2: Same grid + Tier 2 queries
        tier2_yield = len(core_grid) * len(TIER_2_QUERIES) * avg_unique_per_call * 0.5
        plan.add(city_name, core_grid, list(TIER_2_QUERIES))
        estimated_yield += tier2_yield

        if estimated_yield >= target_count * 1.2:
            break

        # Phase 3: Denser grid + Tier 1 (fill gaps)
        dense_grid = generate_grid(
            city_config["bounds"],
            step_km=city_config["base_grid_step_km"] * 0.6,
            strategy="fill_gaps",
            exclude=core_grid,
        )
        plan.add(city_name, dense_grid, list(TIER_1_QUERIES))
        estimated_yield += len(dense_grid) * len(TIER_1_QUERIES) * avg_unique_per_call * 0.3

        if estimated_yield >= target_count * 1.2:
            break

        # Phase 4: Core grid + Tier 3 (niche categories)
        plan.add(city_name, core_grid, list(TIER_3_QUERIES))
        estimated_yield += len(core_grid) * len(TIER_3_QUERIES) * avg_unique_per_call * 0.3

    return plan
