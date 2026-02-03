# pricing_resolver.py - v1.0
# Resolves AWS Backup and S3 storage pricing: tries public price list first (no credentials), then GetProducts.
# Dependencies: boto3, region_mapping, public_pricing. Port: N/A (backend).

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .region_mapping import get_location_for_region
from . import public_pricing as pub

logger = logging.getLogger(__name__)

# AWS Pricing API is only available in us-east-1 (and ap-south-1 for India)
PRICING_REGION = "us-east-1"


@dataclass
class PricingResult:
    """Normalized result: flat rate or tier bands, plus debug payload."""
    rate_per_gb_month: float | None = None  # flat rate
    tiers: list[dict[str, float]] = field(default_factory=list)  # [{from_gb, to_gb, rate_per_gb_month}]
    unit: str = "GB-Mo"
    currency: str = "USD"
    sku: str | None = None
    product_attributes: dict[str, Any] = field(default_factory=dict)
    term_code: str | None = None
    price_dimension: dict[str, Any] = field(default_factory=dict)
    raw_filter_used: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def _normalize_to_gb_month(price_per_unit: float, unit: str) -> float | None:
    """Convert price to USD per GB-Month. Expect unit like 'GB-Mo', 'GB', etc."""
    u = (unit or "").strip().lower()
    if "gb-mo" in u or "gb-month" in u:
        return price_per_unit
    if u == "gb":
        return price_per_unit  # assume per-month if storage
    # Unknown unit
    return None


def _parse_price_dimension(dim: dict[str, Any], currency: str) -> tuple[float | None, str]:
    """Extract price and unit from price dimension. Returns (price_per_gb_month, unit)."""
    price_per_unit = dim.get("pricePerUnit", {}).get(currency)
    if price_per_unit is None:
        return None, dim.get("unit", "")
    try:
        p = float(price_per_unit)
    except (TypeError, ValueError):
        return None, dim.get("unit", "")
    unit = dim.get("unit", "")
    return p, unit


def _build_tier_band(from_gb: float, to_gb: float, rate: float) -> dict[str, float]:
    return {"from_gb": from_gb, "to_gb": to_gb, "rate_per_gb_month": rate}


def get_products(client: Any, service: str, filters: list[dict]) -> list[dict]:
    """Paginate GetProducts and return all product list."""
    out: list[dict] = []
    try:
        paginator = client.get_paginator("get_products")
        for page in paginator.paginate(ServiceCode=service, Filters=filters):
            for price_str in page.get("PriceList", []):
                try:
                    out.append(json.loads(price_str))
                except json.JSONDecodeError:
                    continue
    except (ClientError, NoCredentialsError) as e:
        logger.exception("get_products failed: %s", e)
        raise
    return out


def resolve_aws_backup_storage(
    region_code: str,
    currency: str = "USD",
    client: Any | None = None,
) -> PricingResult:
    """
    Resolve AWS Backup storage pricing for S3 backups in the given region.
    Tries public price list first (no credentials), then GetProducts.
    """
    location = get_location_for_region(region_code)
    if not location:
        return PricingResult(error=f"Unknown region: {region_code}")

    # 1) Try public price list (no credentials required)
    pub_result = pub.resolve_aws_backup_storage_public(region_code, currency)
    if not pub_result.error and pub_result.rate_per_gb_month is not None:
        return PricingResult(
            rate_per_gb_month=pub_result.rate_per_gb_month,
            currency=pub_result.currency,
            unit=pub_result.unit,
            sku=pub_result.sku,
            product_attributes=pub_result.product_attributes,
            term_code=pub_result.term_code,
            price_dimension=pub_result.price_dimension,
            raw_filter_used=pub_result.raw_filter_used,
        )

    # 2) Fallback to Pricing API (requires credentials)
    filters = [
        {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Storage"},
        {"Type": "TERM_MATCH", "Field": "location", "Value": location},
        {"Type": "TERM_MATCH", "Field": "serviceCode", "Value": "AWS Backup"},
    ]
    try:
        c = client or boto3.client("pricing", region_name=PRICING_REGION)
    except NoCredentialsError:
        return PricingResult(
            error=pub_result.error or "Pricing unavailable. Public price list failed; no AWS credentials for API fallback.",
            raw_filter_used=pub_result.raw_filter_used,
        )
    except Exception as e:
        return PricingResult(error=f"Failed to create pricing client: {e}")

    try:
        products = get_products(c, "AWS Backup", filters)
    except NoCredentialsError:
        return PricingResult(
            error=pub_result.error or "Public price list failed; no AWS credentials for API fallback.",
            raw_filter_used=pub_result.raw_filter_used,
        )
    except ClientError as e:
        return PricingResult(error=str(e), raw_filter_used={"filters": filters})
    except Exception as e:
        return PricingResult(error=str(e), raw_filter_used={"filters": filters})

    # Prefer OnDemand, then any term with GB-Mo unit
    best: PricingResult = PricingResult(
        raw_filter_used={"service": "AWS Backup", "location": location, "filters": filters},
    )
    for product in products:
        attrs = product.get("product", {}).get("attributes", {})
        # Optional: filter to S3-related if present
        # if "storageMedia" in attrs and "S3" not in str(attrs.get("storageMedia", "")):
        #     continue
        product_family = attrs.get("productFamily", "")
        if product_family != "Storage":
            continue

        terms = product.get("terms", {}) or {}
        on_demand = terms.get("OnDemand", {})
        for sku, term_detail in on_demand.items():
            for dim_id, dim in (term_detail.get("priceDimensions") or {}).items():
                price_per_unit, unit = _parse_price_dimension(dim, currency)
                if price_per_unit is None:
                    continue
                rate = _normalize_to_gb_month(price_per_unit, unit)
                if rate is not None and rate >= 0:
                    best.rate_per_gb_month = rate
                    best.sku = product.get("product", {}).get("sku")
                    best.product_attributes = attrs
                    best.term_code = "OnDemand"
                    best.price_dimension = dim
                    best.currency = currency
                    best.unit = "GB-Mo"
                    return best

    # If no OnDemand, try Reserved or first Storage term with GB-Mo
    for product in products:
        attrs = product.get("product", {}).get("attributes", {})
        if attrs.get("productFamily") != "Storage":
            continue
        for term_type in ("OnDemand", "Reserved"):
            for sku, term_detail in (product.get("terms", {}).get(term_type) or {}).items():
                for dim_id, dim in (term_detail.get("priceDimensions") or {}).items():
                    price_per_unit, unit = _parse_price_dimension(dim, currency)
                    if price_per_unit is None:
                        continue
                    rate = _normalize_to_gb_month(price_per_unit, unit)
                    if rate is not None and rate >= 0:
                        best.rate_per_gb_month = rate
                        best.sku = product.get("product", {}).get("sku")
                        best.product_attributes = attrs
                        best.term_code = term_type
                        best.price_dimension = dim
                        best.currency = currency
                        best.unit = "GB-Mo"
                        return best

    best.error = "No AWS Backup storage price found for location"
    return best


def resolve_s3_storage(
    region_code: str,
    storage_class: str,
    currency: str = "USD",
    client: Any | None = None,
) -> PricingResult:
    """
    Resolve S3 storage pricing for the given class. Flat rate or tier bands.
    Tries public price list first (no credentials), then GetProducts.
    """
    location = get_location_for_region(region_code)
    if not location:
        return PricingResult(error=f"Unknown region: {region_code}")

    # 1) Try public price list (no credentials required)
    pub_result = pub.resolve_s3_storage_public(region_code, storage_class, currency)
    if not pub_result.error and (pub_result.rate_per_gb_month is not None or pub_result.tiers):
        return PricingResult(
            rate_per_gb_month=pub_result.rate_per_gb_month,
            tiers=pub_result.tiers,
            currency=pub_result.currency,
            unit=pub_result.unit,
            sku=pub_result.sku,
            product_attributes=pub_result.product_attributes,
            term_code=pub_result.term_code,
            price_dimension=pub_result.price_dimension,
            raw_filter_used=pub_result.raw_filter_used,
        )

    # 2) Fallback to Pricing API (requires credentials)
    filters = [
        {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Storage"},
        {"Type": "TERM_MATCH", "Field": "location", "Value": location},
        {"Type": "TERM_MATCH", "Field": "serviceCode", "Value": "Amazon S3"},
        {"Type": "TERM_MATCH", "Field": "storageClass", "Value": storage_class},
    ]
    try:
        c = client or boto3.client("pricing", region_name=PRICING_REGION)
    except NoCredentialsError:
        return PricingResult(
            error=pub_result.error or "Pricing unavailable. Public price list failed; no AWS credentials for API fallback.",
            raw_filter_used=pub_result.raw_filter_used,
        )
    except Exception as e:
        return PricingResult(error=f"Failed to create pricing client: {e}")

    try:
        products = get_products(c, "Amazon S3", filters)
    except NoCredentialsError:
        return PricingResult(
            error=pub_result.error or "Public price list failed; no AWS credentials for API fallback.",
            raw_filter_used=pub_result.raw_filter_used,
        )
    except ClientError as e:
        return PricingResult(error=str(e), raw_filter_used={"filters": filters})
    except Exception as e:
        return PricingResult(error=str(e), raw_filter_used={"filters": filters})

    result = PricingResult(
        raw_filter_used={"service": "Amazon S3", "storageClass": storage_class, "location": location},
    )
    tiers_with_rates: list[tuple[float, float, float]] = []  # (from_gb, to_gb, rate)

    for product in products:
        attrs = product.get("product", {}).get("attributes", {})
        if attrs.get("productFamily") != "Storage":
            continue
        # Tier info may be in usagetype or elsewhere (e.g. "TimedStorage-ByteHrs" with no tier = first tier)
        usage_type = attrs.get("usagetype", "")

        terms = product.get("terms", {}) or {}
        on_demand = terms.get("OnDemand", {})
        for sku, term_detail in on_demand.items():
            for dim_id, dim in (term_detail.get("priceDimensions") or {}).items():
                price_per_unit, unit = _parse_price_dimension(dim, currency)
                if price_per_unit is None:
                    continue
                rate = _normalize_to_gb_month(price_per_unit, unit)
                if rate is None or rate < 0:
                    continue
                # S3 often has tiered usageType like "TimedStorage-ByteHrs" (single tier) or tier-specific
                # For simplicity: collect all and sort by start range; if single price, return flat
                start = 0.0
                end = float("inf")
                # Some SKUs have "beginRange" / "endRange" in price dimension (in GB-Mo or bytes)
                br = dim.get("beginRange")
                er = dim.get("endRange")
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
                tiers_with_rates.append((start, end, rate))
                if result.sku is None:
                    result.sku = product.get("product", {}).get("sku")
                    result.product_attributes = attrs
                    result.term_code = "OnDemand"
                    result.price_dimension = dim
                result.currency = currency
                result.unit = "GB-Mo"

    if not tiers_with_rates:
        result.error = "No S3 storage price found for storage class and location"
        return result

    tiers_with_rates.sort(key=lambda x: x[0])
    if len(tiers_with_rates) == 1 and tiers_with_rates[0][1] == float("inf"):
        result.rate_per_gb_month = tiers_with_rates[0][2]
    else:
        result.tiers = [
            _build_tier_band(f, t, r) for f, t, r in tiers_with_rates
        ]
    return result
