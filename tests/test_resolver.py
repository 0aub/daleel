"""Tests for the region/city name resolver."""

import pytest

from resolver import resolve_input


class TestResolveInput:
    def test_exact_region_name(self):
        targets = resolve_input("Riyadh")
        assert len(targets) == 1
        assert targets[0].region_key == "Riyadh_Region"
        assert targets[0].city_names == []

    def test_arabic_region_name(self):
        targets = resolve_input("الرياض")
        assert len(targets) == 1
        assert targets[0].region_key == "Riyadh_Region"

    def test_city_name_resolves_to_region(self):
        targets = resolve_input("Buraidah")
        assert len(targets) == 1
        assert targets[0].region_key == "Qaseem_Region"
        assert targets[0].city_names == ["Buraidah"]

    def test_case_insensitive(self):
        targets = resolve_input("riyadh")
        assert targets[0].region_key == "Riyadh_Region"

    def test_jeddah_alias(self):
        targets = resolve_input("Jeddah")
        assert len(targets) == 1
        assert targets[0].region_key == "Makkah_Region"
        assert targets[0].city_names == ["Jeddah"]

    def test_comma_separated(self):
        targets = resolve_input("Riyadh,Jeddah")
        assert len(targets) == 2

    def test_all_regions(self):
        targets = resolve_input("all")
        assert len(targets) == 13

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Could not resolve"):
            resolve_input("Atlantis")

    def test_mecca_alias(self):
        targets = resolve_input("mecca")
        assert targets[0].region_key == "Makkah_Region"
        assert targets[0].city_names == []  # "mecca" is a region alias
