# public_pricing.py - v1.0
# Fetches AWS pricing from public price list URLs (no credentials).
# Dependencies: region_mapping. Port: N/A (backend).

from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .region_mapping import get_location_for_region

logger = logging.getLogger(__name__)

BASE_URL = "https://pricing.us-east-1.amazonaws.com"
OFFERS_BASE = f"{BASE_URL}/offers/v1.0/aws"
# Service codes in public index: AmazonS3; AWS Backup may be under different code
SERVICE_CODE_S3 = "AmazonS3"
SERVICE_CODE_BACKUP = "AWSBackup"


@dataclass
class PricingResult:
    """Same shape as pricing_resolver.PricingResult for compatibility."""
    rate_per_gb_month: float | None = None
    tiers: list[dict[str, float]] = field(default_factory=list)
    unit: str = "GB-Mo"
    currency: str = "USD"
    sku: str | None = None
    product_attributes: dict[str, Any] = field(default_factory=dict)
    term_code: str | None = None
    price_dimension: dict[str, Any] = field(default_factory=dict)
    raw_filter_used: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def _fetch_json(url: str, timeout: int = 90) -> tuple[dict[str, Any] | None, str]:
    """
    GET URL and parse JSON. Returns (data, error_message).
    Uses User-Agent so public AWS price list accepts the request.
    """
    headers = {
        "Accept": "application/json",
        "User-Agent": "awspricing/1.0 (public price list client)",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode()), ""
    except urllib.error.HTTPError as e:
        msg = f"HTTP {e.code}: {e.reason}"
        logger.warning("Failed to fetch %s: %s", url, msg)
        return None, msg
    except urllib.error.URLError as e:
        msg = str(e.reason) if e.reason else str(e)
        logger.warning("Failed to fetch %s: %s", url, msg)
        return None, msg
    except Exception as e:
        msg = str(e)
        logger.warning("Failed to fetch %s: %s", url, msg)
        return None, msg


def _normalize_to_gb_month(price_per_unit: float, unit: str) -> float | None:
    u = (unit or "").strip().lower()
    if "gb-mo" in u or "gb-month" in u or u == "gb":
        return price_per_unit
    return None


def _parse_price_dimension(dim: dict[str, Any], currency: str) -> tuple[float | None, str]:
    # Public JSON uses pricePerUnit; support both dict and direct access
    pu = dim.get("pricePerUnit")
    if isinstance(pu, dict):
        price_per_unit = pu.get(currency)
    else:
        price_per_unit = None
    if price_per_unit is None:
        return None, dim.get("unit", "")
    try:
        p = float(price_per_unit)
    except (TypeError, ValueError):
        return None, dim.get("unit", "")
    return p, dim.get("unit", "")


def _build_tier_band(from_gb: float, to_gb: float, rate: float) -> dict[str, float]:
    return {"from_gb": from_gb, "to_gb": to_gb, "rate_per_gb_month": rate}


def _get_offer_url_global(service_code: str) -> str:
    """Single global file: all regions in one JSON (no credentials)."""
    return f"{OFFERS_BASE}/{service_code}/current/index.json"


def _get_offer_url_regional(service_code: str, region_code: str) -> str:
    """Regional file: .../serviceCode/current/regionCode/index.json"""
    return f"{OFFERS_BASE}/{service_code}/current/{region_code}/index.json"


def _resolve_offer_url(service_code: str) -> str | None:
    """
    Fetch main index and get currentVersionUrl for the service (exact URL from AWS).
    Returns full URL or None if not found.
    """
    index_url = f"{OFFERS_BASE}/index.json"
    data, _ = _fetch_json(index_url)
    if not data:
        return None
    offers = data.get("offers") or {}
    offer = offers.get(service_code)
    if not offer:
        return None
    rel = offer.get("currentVersionUrl") or offer.get("currentRegionIndexUrl")
    if not rel or not isinstance(rel, str):
        return None
    if rel.startswith("/"):
        return f"{BASE_URL}{rel}"
    return f"{OFFERS_BASE}/{rel}" if not rel.startswith("http") else rel


def _discover_backup_offer_code() -> str | None:
    """Discover AWS Backup offer code from main index (may be AWSBackup, awspricing, etc.)."""
    index_url = f"{OFFERS_BASE}/index.json"
    data, _ = _fetch_json(index_url)
    if not data:
        return None
    offers = data.get("offers") or {}
    for code, _ in offers.items():
        if code and "backup" in code.lower():
            return code
    return None


def _range_from_dim(dim: dict[str, Any]) -> tuple[float, float]:
    """Get begin/end range from price dimension; support both key naming conventions."""
    start = 0.0
    end = float("inf")
    br = dim.get("beginRange") or dim.get("startingRange")
    er = dim.get("endRange") or dim.get("endingRange")
    if br is not None:
        try:
            start = float(br)
        except (TypeError, ValueError):
            pass
    if er is not None:
        try:
            end = float(er)
        except (TypeError, ValueError):
            pass
    return start, end


def _backup_storage_match(attrs: dict[str, Any], location: str) -> bool:
    """True if product looks like Backup storage for the given location."""
    loc = (attrs.get("location") or "").strip()
    if loc != location:
        return False
    pf = (attrs.get("productFamily") or "").strip().lower()
    # Accept Storage, Backup Storage, or any product with backup-related usage
    if pf in ("storage", "backup storage", "backup"):
        return True
    ut = (attrs.get("usagetype") or attrs.get("usageType") or "").lower()
    if "backup" in ut and "storage" in ut:
        return True
    if pf and "storage" in pf:
        return True
    return False


def resolve_aws_backup_storage_public(
    region_code: str,
    currency: str = "USD",
) -> PricingResult:
    """
    Resolve AWS Backup storage pricing from public price list (no credentials).
    Tries discovered Backup offer code from index, then AWSBackup. Relaxed product filter.
    """
    location = get_location_for_region(region_code)
    if not location:
        return PricingResult(error=f"Unknown region: {region_code}")

    fetch_error = ""
    data = None
    url = None
    # Try discovered offer code first, then known code
    for service_code in (_discover_backup_offer_code(), SERVICE_CODE_BACKUP):
        if not service_code:
            continue
        url = _resolve_offer_url(service_code)
        if url:
            data, fetch_error = _fetch_json(url)
            if data:
                break
        if not data:
            url = _get_offer_url_global(service_code)
            data, fetch_error2 = _fetch_json(url)
            if fetch_error2:
                fetch_error = fetch_error2
            if data:
                break
        if not data:
            url = _get_offer_url_regional(service_code, region_code)
            data, fetch_error2 = _fetch_json(url)
            if fetch_error2:
                fetch_error = fetch_error2
        if data:
            break

    if not data:
        return PricingResult(
            error=f"AWS Backup not in public price list. {fetch_error or 'Try Pricing API with credentials for Backup.'}",
            raw_filter_used={"service": "AWS Backup", "region": region_code, "url": url},
        )

    products = data.get("products") or {}
    terms = data.get("terms") or {}
    on_demand = terms.get("OnDemand") or {}

    best = PricingResult(
        raw_filter_used={"service": "AWS Backup (public)", "location": location, "url": url},
    )
    for sku, product in products.items():
        attrs = product.get("attributes") or {}
        if not _backup_storage_match(attrs, location):
            continue
        if sku not in on_demand:
            continue
        term_entries = on_demand[sku]
        for term_sku, term_detail in term_entries.items():
            dims = term_detail.get("priceDimensions") or {}
            for dim_id, dim in dims.items():
                price_per_unit, unit = _parse_price_dimension(dim, currency)
                if price_per_unit is None:
                    continue
                rate = _normalize_to_gb_month(price_per_unit, unit)
                if rate is not None and rate >= 0:
                    best.rate_per_gb_month = rate
                    best.sku = sku
                    best.product_attributes = dict(attrs)
                    best.term_code = "OnDemand"
                    best.price_dimension = dict(dim)
                    best.currency = currency
                    best.unit = "GB-Mo"
                    return best

    # Not found: return a message that doesn't mention credentials; S3 can still work
    best.error = "AWS Backup storage not in public price list for this region. S3 comparison below uses public pricing."
    return best


def resolve_s3_storage_public(
    region_code: str,
    storage_class: str,
    currency: str = "USD",
) -> PricingResult:
    """
    Resolve S3 storage pricing from public price list (no credentials).
    Tries global URL first (all regions in one file), then regional. Filters Storage, location, storageClass.
    """
    location = get_location_for_region(region_code)
    if not location:
        return PricingResult(error=f"Unknown region: {region_code}")

    fetch_error = ""
    url = _resolve_offer_url(SERVICE_CODE_S3)
    if url:
        data, fetch_error = _fetch_json(url)
    else:
        data, fetch_error = None, ""
    if not data:
        url = _get_offer_url_global(SERVICE_CODE_S3)
        data, fetch_error2 = _fetch_json(url)
        if fetch_error2:
            fetch_error = fetch_error2
    if not data:
        url = _get_offer_url_regional(SERVICE_CODE_S3, region_code)
        data, fetch_error2 = _fetch_json(url)
        if fetch_error2:
            fetch_error = fetch_error2
    if not data:
        return PricingResult(
            error=f"Public price list (S3) unavailable. {fetch_error or 'Check network.'}",
            raw_filter_used={"service": SERVICE_CODE_S3, "region": region_code, "url": url},
        )

    products = data.get("products") or {}
    terms = data.get("terms") or {}
    on_demand = terms.get("OnDemand") or {}

    result = PricingResult(
        raw_filter_used={
            "service": "Amazon S3 (public)",
            "storageClass": storage_class,
            "location": location,
            "url": url,
        },
    )
    tiers_with_rates: list[tuple[float, float, float]] = []

    for sku, product in products.items():
        attrs = product.get("attributes") or {}
        if attrs.get("productFamily") != "Storage":
            continue
        if attrs.get("location") != location:
            continue
        # storageClass in public list: "General Purpose" for Standard, "Standard-IA", etc.
        sc = (attrs.get("storageClass") or attrs.get("storage class") or "").strip().lower()
        want = storage_class.strip().lower()
        if sc:
            if want == "standard" and ("general" in sc or sc == "standard"):
                pass
            elif want != sc and want not in sc and sc not in want:
                continue
        if sku not in on_demand:
            continue
        term_entries = on_demand[sku]
        for term_sku, term_detail in term_entries.items():
            for dim_id, dim in (term_detail.get("priceDimensions") or {}).items():
                price_per_unit, unit = _parse_price_dimension(dim, currency)
                if price_per_unit is None:
                    continue
                rate = _normalize_to_gb_month(price_per_unit, unit)
                if rate is None or rate < 0:
                    continue
                start, end = _range_from_dim(dim)
                tiers_with_rates.append((start, end, rate))
                if result.sku is None:
                    result.sku = sku
                    result.product_attributes = dict(attrs)
                    result.term_code = "OnDemand"
                    result.price_dimension = dict(dim)
                result.currency = currency
                result.unit = "GB-Mo"

    if not tiers_with_rates:
        result.error = "No S3 storage price found for storage class and location in public price list"
        return result

    tiers_with_rates.sort(key=lambda x: x[0])
    if len(tiers_with_rates) == 1 and tiers_with_rates[0][1] == float("inf"):
        result.rate_per_gb_month = tiers_with_rates[0][2]
    else:
        result.tiers = [_build_tier_band(f, t, r) for f, t, r in tiers_with_rates]
    return result
