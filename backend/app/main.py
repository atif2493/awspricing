# main.py - v1.0
# FastAPI app: pricing endpoints, calc, health. Deps: pricing_resolver, cost_engine, cache.
# Port: 8000

from __future__ import annotations

import os
import time
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .cache import TTLCache
from .cost_engine import (
    TierBand,
    aws_backup_total,
    copy_multiplier,
    cost_from_flat_rate,
    cost_from_tiers,
    delta_pct,
    delta_usd,
    s3_versioning_total,
    tb_to_gb,
    versioned_gb,
)
from .pricing_resolver import (
    PricingResult,
    resolve_aws_backup_storage,
    resolve_s3_storage,
)

app = FastAPI(
    title="awspricing",
    description="Live AWS Backup vs S3 versioning cost calculator",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE_TTL = float(os.environ.get("PRICING_CACHE_TTL_SECONDS", "86400"))  # 24h
pricing_cache = TTLCache(ttl_seconds=CACHE_TTL)


# --- Request/Response models ---

class PricingContext(BaseModel):
    region: str = "us-east-1"
    currency: str = "USD"
    tb_binary: bool = True  # True = 1024 GB per TB


class CalcInput(BaseModel):
    data_tb: float = Field(..., ge=0)
    tb_binary: bool = True
    region: str = "us-east-1"
    currency: str = "USD"
    # AWS Backup
    aws_backup_rate_per_gb_month: float | None = None  # from /api/pricing/aws-backup
    # S3 versioning
    s3_storage_class: str = "Standard"
    versioning_overhead_pct: float = Field(0.25, ge=0, le=2)
    s3_tiers: list[dict[str, float]] | None = None  # [{from_gb, to_gb, rate_per_gb_month}]
    s3_flat_rate_per_gb_month: float | None = None  # if no tiers
    # Add-ons
    num_copy_addons: int = Field(0, ge=0)
    flat_addon_usd: float = Field(0, ge=0)


# --- Pricing endpoints (with optional cache bypass) ---

@app.get("/api/pricing/aws-backup")
def get_aws_backup_pricing(
    region: str = Query("us-east-1"),
    currency: str = Query("USD"),
    refresh: bool = Query(False, description="Bypass cache"),
) -> dict[str, Any]:
    """Return AWS Backup storage pricing for S3 backups. Rate normalized to USD/GB-month."""
    if refresh:
        pricing_cache.invalidate(service="AWS Backup", region=region, currency=currency)
    hit = pricing_cache.get(service="AWS Backup", region=region, currency=currency)
    if hit is not None:
        data, cached_at = hit
        return {**data, "cached_at": cached_at, "from_cache": True}
    result = resolve_aws_backup_storage(region_code=region, currency=currency)
    if result.error:
        return {
            "error": result.error,
            "rate_per_gb_month": None,
            "sku": result.sku,
            "product_attributes": result.product_attributes,
            "term_code": result.term_code,
            "raw_filter": result.raw_filter_used,
        }
    data = {
        "rate_per_gb_month": result.rate_per_gb_month,
        "currency": result.currency,
        "unit": result.unit,
        "sku": result.sku,
        "product_attributes": result.product_attributes,
        "term_code": result.term_code,
        "price_dimension": result.price_dimension,
        "raw_filter": result.raw_filter_used,
    }
    pricing_cache.set(data, service="AWS Backup", region=region, currency=currency)
    return {**data, "cached_at": time.monotonic(), "from_cache": False}


@app.get("/api/pricing/s3-storage")
def get_s3_storage_pricing(
    region: str = Query("us-east-1"),
    currency: str = Query("USD"),
    storageClass: str = Query("Standard"),
    refresh: bool = Query(False),
) -> dict[str, Any]:
    """Return S3 storage pricing. Flat rate or tier bands, normalized to USD/GB-month."""
    if refresh:
        pricing_cache.invalidate(
            service="Amazon S3", region=region, currency=currency, storage_class=storageClass
        )
    hit = pricing_cache.get(
        service="Amazon S3", region=region, currency=currency, storage_class=storageClass
    )
    if hit is not None:
        data, cached_at = hit
        return {**data, "cached_at": cached_at, "from_cache": True}
    result = resolve_s3_storage(
        region_code=region, storage_class=storageClass, currency=currency
    )
    if result.error:
        return {
            "error": result.error,
            "rate_per_gb_month": None,
            "tiers": [],
            "sku": result.sku,
            "product_attributes": result.product_attributes,
            "raw_filter": result.raw_filter_used,
        }
    # JSON does not support Infinity; use a large sentinel for open-ended tiers
    tiers_json = []
    for t in result.tiers:
        to_gb = t["to_gb"]
        if to_gb == float("inf") or to_gb > 1e35:
            to_gb = 1e40
        tiers_json.append({**t, "to_gb": to_gb})
    data = {
        "rate_per_gb_month": result.rate_per_gb_month,
        "tiers": tiers_json,
        "currency": result.currency,
        "unit": result.unit,
        "sku": result.sku,
        "product_attributes": result.product_attributes,
        "term_code": result.term_code,
        "price_dimension": result.price_dimension,
        "raw_filter": result.raw_filter_used,
    }
    pricing_cache.set(
        data,
        service="Amazon S3",
        region=region,
        currency=currency,
        storage_class=storageClass,
    )
    return {**data, "cached_at": time.monotonic(), "from_cache": False}


# --- Calc (server-side optional; frontend can compute with fetched rates) ---

@app.post("/api/calc")
def post_calc(body: CalcInput) -> dict[str, Any]:
    """
    Compute preset table (10–90 TB) and comparison table using provided rates.
    Frontend should fetch pricing first, then call this or compute client-side.
    """
    gb = tb_to_gb(body.data_tb, body.tb_binary)
    copy_mult = copy_multiplier(body.num_copy_addons)

    # AWS Backup
    awb_rate = body.aws_backup_rate_per_gb_month
    awb_base_cost = cost_from_flat_rate(gb, awb_rate) if awb_rate is not None else None
    awb_total = (
        aws_backup_total(gb, awb_rate, copy_mult, body.flat_addon_usd)
        if awb_rate is not None
        else None
    )

    # S3 versioning
    v_gb = versioned_gb(gb, body.versioning_overhead_pct)
    if body.s3_tiers:
        tiers = [
            TierBand(b["from_gb"], b["to_gb"], b["rate_per_gb_month"])
            for b in body.s3_tiers
        ]
        tiers.sort(key=lambda t: t.from_gb)
        s3_base_cost = cost_from_tiers(v_gb, tiers)
    elif body.s3_flat_rate_per_gb_month is not None:
        tiers = [TierBand(0, float("inf"), body.s3_flat_rate_per_gb_month)]
        s3_base_cost = cost_from_flat_rate(v_gb, body.s3_flat_rate_per_gb_month)
    else:
        tiers = []
        s3_base_cost = None

    if tiers:
        s3_total = s3_versioning_total(
            gb,
            body.versioning_overhead_pct,
            tiers,
            copy_mult,
            body.flat_addon_usd,
        )
    else:
        s3_total = None

    reference = awb_total if awb_total is not None else 0
    return {
        "data_tb": body.data_tb,
        "data_gb": gb,
        "versioned_gb": v_gb,
        "aws_backup": {
            "rate_per_gb_month": awb_rate,
            "base_cost_usd": awb_base_cost,
            "total_usd": awb_total,
            "copy_multiplier": copy_mult,
        },
        "s3_versioning": {
            "effective_gb": v_gb,
            "base_cost_usd": s3_base_cost,
            "total_usd": s3_total,
            "copy_multiplier": copy_mult,
        },
        "deltas_vs_aws_backup": {
            "aws_backup_total_usd": awb_total,
            "s3_total_usd": s3_total,
            "s3_delta_usd": delta_usd(s3_total or 0, reference) if s3_total is not None else None,
            "s3_delta_pct": delta_pct(s3_total or 0, reference) if s3_total is not None else None,
        },
    }


@app.get("/api/regions")
def list_regions() -> list[dict[str, str]]:
    """List supported regions (code + location name)."""
    from .region_mapping import REGION_TO_LOCATION
    return [{"code": k, "location": v} for k, v in REGION_TO_LOCATION.items()]


@app.get("/health")
def health() -> dict[str, str]:
    """Health check for container orchestration."""
    return {"status": "ok", "service": "awspricing-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
