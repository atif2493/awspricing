# test_region_mapping.py - v1.0
# Unit tests: region code to Pricing API location mapping.
# Dependencies: region_mapping. Port: N/A.

import pytest
from app.region_mapping import (
    REGION_TO_LOCATION,
    LOCATION_TO_REGION,
    get_location_for_region,
    get_region_for_location,
)


def test_us_east_1():
    assert get_location_for_region("us-east-1") == "US East (N. Virginia)"
    assert get_location_for_region("US-EAST-1") == "US East (N. Virginia)"


def test_unknown_region():
    assert get_location_for_region("xx-unknown-1") is None


def test_location_to_region():
    assert get_region_for_location("US East (N. Virginia)") == "us-east-1"
    assert get_region_for_location("EU (Ireland)") == "eu-west-1"


def test_roundtrip():
    for code, location in REGION_TO_LOCATION.items():
        assert get_region_for_location(location) == code
        assert get_location_for_region(code) == location


def test_loc_to_region_unknown():
    assert get_region_for_location("Unknown Location") is None
