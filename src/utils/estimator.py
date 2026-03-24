"""Pre-run cost estimator for API calls.

Calculates estimated API calls, cost, and time before any money is spent.
Displays a formatted estimate and asks for user confirmation.
"""

from dataclasses import dataclass

__all__ = ["CostEstimate", "estimate_cost", "display_estimate"]


@dataclass
class CostEstimate:
    """Cost estimation result."""

    target_unique: int
    estimated_raw_results: int
    estimated_api_calls: int
    estimated_cost_usd: float
    estimated_time_minutes: float
    within_free_tier: bool


def estimate_cost(total_population: int, target_count: int) -> CostEstimate:
    """Calculate estimated API calls and cost based on region density and target.

    Assumptions based on Google Places API behavior in Saudi Arabia:
    - Dense urban areas: ~8-12 unique results per call
    - Sparse areas: ~4-6 unique results per call
    - Deduplication ratio: ~55-65% are unique
    - Cost per 1,000 Text Search (New) calls: $32
    """
    if total_population > 2_000_000:
        dedup_ratio = 0.55
    elif total_population > 500_000:
        dedup_ratio = 0.60
    elif total_population > 100_000:
        dedup_ratio = 0.65
    else:
        dedup_ratio = 0.70

    raw_results_needed = int(target_count / dedup_ratio)
    avg_results_per_call = 14
    estimated_api_calls = int(raw_results_needed / avg_results_per_call)
    estimated_api_calls = int(estimated_api_calls * 1.15)  # 15% buffer

    cost_per_call = 0.032
    estimated_cost = estimated_api_calls * cost_per_call
    estimated_minutes = (estimated_api_calls * 0.2) / 60

    return CostEstimate(
        target_unique=target_count,
        estimated_raw_results=raw_results_needed,
        estimated_api_calls=estimated_api_calls,
        estimated_cost_usd=round(estimated_cost, 2),
        estimated_time_minutes=round(estimated_minutes, 1),
        within_free_tier=estimated_cost <= 200,
    )


def display_estimate(estimate: CostEstimate, region_name: str, cities: list[str]) -> None:
    """Print a formatted cost estimate box to the terminal."""
    free_status = "Within free tier" if estimate.within_free_tier else "EXCEEDS free tier"

    print()
    print("=" * 58)
    print("   daleel (دليل) — Cost Estimate")
    print("=" * 58)
    print()
    print(f"   Region:              {region_name}")
    print(f"   Target:              {estimate.target_unique:,} unique businesses")
    print()
    print(f"   Estimated API calls: ~{estimate.estimated_api_calls:,}")
    print(f"   Estimated cost:      ~${estimate.estimated_cost_usd:.2f}")
    print(f"   Estimated time:      ~{estimate.estimated_time_minutes} minutes")
    print(f"   Free tier ($200/mo): {free_status}")
    print()
    if cities:
        print("   Cities to cover:")
        for city in cities:
            print(f"     - {city}")
        print()
    print("=" * 58)
    print()
