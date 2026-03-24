"""Center-first grid point generator.

Generates lat/lng grid points starting from the city center and expanding outward,
ensuring the most business-dense areas are searched first.
"""

from math import cos, radians

__all__ = ["GridPoint", "generate_grid"]

# Type alias for a grid point (latitude, longitude)
GridPoint = tuple[float, float]


def generate_grid(
    bounds: dict,
    step_km: float,
    strategy: str = "center_first",
    exclude: list[GridPoint] | None = None,
) -> list[GridPoint]:
    """Generate grid points within bounds, sorted by distance from center.

    Args:
        bounds: Dict with keys "north", "south", "east", "west" (degrees).
        step_km: Distance between grid points in kilometers.
        strategy: "center_first" sorts nearest-to-center first.
                  "fill_gaps" generates intermediate points excluding existing ones.
        exclude: Grid points to exclude (used with fill_gaps strategy).

    Returns:
        List of (latitude, longitude) tuples sorted by distance from center.
    """
    center_lat = (bounds["north"] + bounds["south"]) / 2
    center_lng = (bounds["east"] + bounds["west"]) / 2

    # Convert km to degrees (approximate at Saudi latitudes ~17-32°N)
    lat_step = step_km / 111.0  # 1° lat ≈ 111 km
    lng_step = step_km / (111.0 * cos(radians(center_lat)))

    points: list[GridPoint] = []
    lat = bounds["south"]
    while lat <= bounds["north"]:
        lng = bounds["west"]
        while lng <= bounds["east"]:
            points.append((round(lat, 6), round(lng, 6)))
            lng += lng_step
        lat += lat_step

    # Remove excluded points if doing gap-fill
    if exclude:
        exclude_set = set(exclude)
        points = [p for p in points if p not in exclude_set]

    if strategy == "center_first":
        points.sort(key=lambda p: (p[0] - center_lat) ** 2 + (p[1] - center_lng) ** 2)

    return points
