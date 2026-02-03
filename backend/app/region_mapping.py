# region_mapping.py - v1.0
# Maps AWS region codes to Pricing API "location" strings. Used by pricing resolver.
# Dependencies: none. Port: N/A (backend internal).

# AWS Pricing API uses "location" in product attributes; regions use codes like us-east-1.
# Pricing API is typically called from us-east-1; location filter selects the region's prices.
REGION_TO_LOCATION: dict[str, str] = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "af-south-1": "Africa (Cape Town)",
    "ap-east-1": "Asia Pacific (Hong Kong)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-south-2": "Asia Pacific (Hyderabad)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-southeast-3": "Asia Pacific (Jakarta)",
    "ap-southeast-4": "Asia Pacific (Melbourne)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "ap-northeast-3": "Asia Pacific (Osaka)",
    "ca-central-1": "Canada (Central)",
    "ca-west-1": "Canada West (Calgary)",
    "eu-central-1": "EU (Frankfurt)",
    "eu-central-2": "EU (Zurich)",
    "eu-west-1": "EU (Ireland)",
    "eu-west-2": "EU (London)",
    "eu-west-3": "EU (Paris)",
    "eu-north-1": "EU (Stockholm)",
    "eu-south-1": "EU (Milan)",
    "eu-south-2": "EU (Spain)",
    "me-south-1": "Middle East (Bahrain)",
    "me-central-1": "Middle East (UAE)",
    "sa-east-1": "South America (São Paulo)",
}

# Reverse: location string -> primary region code (for display)
LOCATION_TO_REGION: dict[str, str] = {v: k for k, v in REGION_TO_LOCATION.items()}


def get_location_for_region(region_code: str) -> str | None:
    """Return Pricing API location string for a region code, or None if unknown."""
    return REGION_TO_LOCATION.get(region_code.strip().lower())


def get_region_for_location(location: str) -> str | None:
    """Return region code for a Pricing API location string."""
    return LOCATION_TO_REGION.get(location)
