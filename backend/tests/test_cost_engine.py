# test_cost_engine.py - v1.0
# Unit tests: TB/GB conversion, versioning overhead, copy multiplier, tier math.
# Dependencies: cost_engine. Port: N/A.

import pytest
from app.cost_engine import (
    TB_CONVERSION_BINARY,
    TB_CONVERSION_DECIMAL,
    TierBand,
    aws_backup_total,
    copy_multiplier,
    cost_from_flat_rate,
    cost_from_tiers,
    delta_pct,
    delta_usd,
    gb_to_tb,
    s3_versioning_total,
    tb_to_gb,
    versioned_gb,
)


def test_tb_to_gb_binary():
    assert tb_to_gb(1, binary=True) == 1024
    assert tb_to_gb(10, binary=True) == 10240
    assert tb_to_gb(0.5, binary=True) == 512


def test_tb_to_gb_decimal():
    assert tb_to_gb(1, binary=False) == 1000
    assert tb_to_gb(10, binary=False) == 10000


def test_gb_to_tb_binary():
    assert gb_to_tb(1024, binary=True) == 1.0
    assert gb_to_tb(10240, binary=True) == 10.0


def test_gb_to_tb_decimal():
    assert gb_to_tb(1000, binary=False) == 1.0


def test_versioned_gb():
    assert versioned_gb(1000, 0) == 1000
    assert versioned_gb(1000, 0.25) == 1250
    assert versioned_gb(1000, 0.5) == 1500


def test_copy_multiplier():
    assert copy_multiplier(0) == 1.0
    assert copy_multiplier(1) == 2.0
    assert copy_multiplier(3) == 4.0
    assert copy_multiplier(-1) == 1.0  # max(0, -1) = 0


def test_cost_from_flat_rate():
    assert cost_from_flat_rate(1000, 0.05) == 50.0
    assert cost_from_flat_rate(0, 0.05) == 0.0


def test_cost_from_tiers_single():
    tiers = [TierBand(0, float("inf"), 0.023)]
    assert cost_from_tiers(1000, tiers) == pytest.approx(23.0)
    assert cost_from_tiers(0, tiers) == 0.0


def test_cost_from_tiers_multiple():
    # 0-50TB @ 0.023, 50TB+ @ 0.022
    tiers = [
        TierBand(0, 50 * 1024, 0.023),
        TierBand(50 * 1024, float("inf"), 0.022),
    ]
    gb_40tb = 40 * 1024
    assert cost_from_tiers(gb_40tb, tiers) == pytest.approx(gb_40tb * 0.023)
    gb_60tb = 60 * 1024
    cost_60 = 50 * 1024 * 0.023 + 10 * 1024 * 0.022
    assert cost_from_tiers(gb_60tb, tiers) == pytest.approx(cost_60)


def test_aws_backup_total():
    # 1024 GB * 0.05 * 1 + 0 = 51.2
    assert aws_backup_total(1024, 0.05, 1.0, 0) == pytest.approx(51.2)
    # with 2x copy + $10 flat
    assert aws_backup_total(1024, 0.05, 2.0, 10) == pytest.approx(51.2 * 2 + 10)


def test_s3_versioning_total():
    tiers = [TierBand(0, float("inf"), 0.023)]
    # base 1000 GB, 25% overhead => 1250 GB, * 0.023 = 28.75
    assert s3_versioning_total(1000, 0.25, tiers, 1.0, 0) == pytest.approx(28.75)
    assert s3_versioning_total(1000, 0.25, tiers, 2.0, 5) == pytest.approx(28.75 * 2 + 5)


def test_delta_usd():
    assert delta_usd(100, 80) == 20
    assert delta_usd(80, 100) == -20


def test_delta_pct():
    assert delta_pct(100, 80) == 25.0
    assert delta_pct(80, 100) == -20.0
    assert delta_pct(50, 0) == 0.0
