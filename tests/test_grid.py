"""Tests for the grid point generator."""

from grid import generate_grid


class TestGenerateGrid:
    RIYADH_BOUNDS = {"north": 24.85, "south": 24.55, "west": 46.55, "east": 46.85}

    def test_generates_points(self):
        points = generate_grid(self.RIYADH_BOUNDS, step_km=5.0)
        assert len(points) > 0

    def test_all_points_within_bounds(self):
        points = generate_grid(self.RIYADH_BOUNDS, step_km=3.0)
        for lat, lng in points:
            assert self.RIYADH_BOUNDS["south"] <= lat <= self.RIYADH_BOUNDS["north"] + 0.01
            assert self.RIYADH_BOUNDS["west"] <= lng <= self.RIYADH_BOUNDS["east"] + 0.01

    def test_center_first_ordering(self):
        points = generate_grid(self.RIYADH_BOUNDS, step_km=3.0, strategy="center_first")
        center_lat = (self.RIYADH_BOUNDS["north"] + self.RIYADH_BOUNDS["south"]) / 2
        center_lng = (self.RIYADH_BOUNDS["east"] + self.RIYADH_BOUNDS["west"]) / 2

        # First point should be closest to center
        first_dist = (points[0][0] - center_lat) ** 2 + (points[0][1] - center_lng) ** 2
        last_dist = (points[-1][0] - center_lat) ** 2 + (points[-1][1] - center_lng) ** 2
        assert first_dist <= last_dist

    def test_smaller_step_more_points(self):
        large = generate_grid(self.RIYADH_BOUNDS, step_km=5.0)
        small = generate_grid(self.RIYADH_BOUNDS, step_km=2.0)
        assert len(small) > len(large)

    def test_exclude_removes_points(self):
        full = generate_grid(self.RIYADH_BOUNDS, step_km=3.0)
        excluded = generate_grid(
            self.RIYADH_BOUNDS, step_km=3.0, strategy="fill_gaps", exclude=full
        )
        assert len(excluded) == 0

    def test_returns_tuples(self):
        points = generate_grid(self.RIYADH_BOUNDS, step_km=5.0)
        for p in points:
            assert isinstance(p, tuple)
            assert len(p) == 2
