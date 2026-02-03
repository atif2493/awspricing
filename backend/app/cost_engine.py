# cost_engine.py - v1.0
# Pure cost math: TB/GB conversion, versioning overhead, copy multiplier, tier bands.
# Dependencies: none. Port: N/A (backend internal).

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

TB_CONVERSION_BINARY = 1024
TB_CONVERSION_DECIMAL = 1000


def tb_to_gb(tb: float, binary: bool = True) -> float:
    """Convert TB to GB. binary=True => 1 TB = 1024 GB, else 1000 GB."""
    mult = TB_CONVERSION_BINARY if binary else TB_CONVERSION_DECIMAL
    return tb * mult


def gb_to_tb(gb: float, binary: bool = True) -> float:
    """Convert GB to TB."""
    mult = TB_CONVERSION_BINARY if binary else TB_CONVERSION_DECIMAL
    return gb / mult


@dataclass
class TierBand:
    """One tier: from_gb (inclusive) to to_gb (exclusive), rate per GB-month in USD."""
    from_gb: float
    to_gb: float  # use float('inf') for open-ended
    rate_per_gb_month: float


def versioned_gb(base_gb: float, overhead_pct: float) -> float:
    """Effective stored GB with versioning overhead. overhead_pct in 0–1 (e.g. 0.25 = 25%)."""
    return base_gb * (1.0 + overhead_pct)


def copy_multiplier(num_copy_addons: int) -> float:
    """copy_multiplier = 1 + number_of_enabled_copy_addons."""
    return 1.0 + max(0, num_copy_addons)


def cost_from_flat_rate(gb: float, rate_per_gb_month: float) -> float:
    """Monthly cost = GB * rate_per_gb_month (USD)."""
    return gb * rate_per_gb_month


def cost_from_tiers(gb: float, tiers: list[TierBand]) -> float:
    """Blended monthly cost using tier bands. Tiers must be sorted by from_gb."""
    total = 0.0
    remaining = gb
    for band in tiers:
        if remaining <= 0:
            break
        band_size = min(remaining, (band.to_gb - band.from_gb) if band.to_gb != float("inf") else remaining)
        if band_size > 0:
            total += band_size * band.rate_per_gb_month
        remaining -= band_size
    return total


def aws_backup_total(
    base_gb: float,
    rate_per_gb_month: float,
    copy_mult: float,
    flat_addon_usd: float = 0.0,
) -> float:
    """AWS Backup total = (base_gb * rate) * copy_mult + flat_addon_usd."""
    base_cost = cost_from_flat_rate(base_gb, rate_per_gb_month)
    return base_cost * copy_mult + flat_addon_usd


def s3_versioning_total(
    base_gb: float,
    overhead_pct: float,
    tiers: list[TierBand],
    copy_mult: float = 1.0,
    flat_addon_usd: float = 0.0,
) -> float:
    """S3 versioning: versioned_gb from tiers, then * copy_mult + flat."""
    v_gb = versioned_gb(base_gb, overhead_pct)
    base_cost = cost_from_tiers(v_gb, tiers)
    return base_cost * copy_mult + flat_addon_usd


def delta_usd(cost: float, reference: float) -> float:
    """cost - reference."""
    return cost - reference


def delta_pct(cost: float, reference: float) -> float:
    """(cost - reference) / reference * 100, or 0 if reference is 0."""
    if reference == 0:
        return 0.0
    return (cost - reference) / reference * 100.0
