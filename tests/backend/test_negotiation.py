"""
Tests for AutoValue Negotiation Intelligence Service (Phase 11).
Validates conservative, aggressive, and evidence-supported negotiation targets,
talking points, and disclaimer notices.
"""
import pytest
from backend.app.services.negotiation_service import negotiation_service


def test_negotiation_targets_monotonicity():
    """Ensure aggressive_target <= evidence_supported_target <= conservative_target."""
    res = negotiation_service.analyze_negotiation(
        asking_price=1320000,
        estimated_value=1210000,
        model_interval_low=1150000,
        model_interval_high=1270000,
        market_median=1240000,
        market_p25=1180000,
        market_p75=1280000,
        comparable_count=6
    )
    assert res.aggressive_target <= res.evidence_supported_target
    assert res.evidence_supported_target <= res.conservative_target
    assert res.asking_price == 1320000
    assert res.negotiation_gap > 0
    assert "Evidence-supported negotiation range" in res.disclaimer
    assert len(res.talking_points) >= 2


def test_negotiation_buyer_leverage_high_asking_price():
    """Asking price well above market generates strong buyer leverage."""
    res = negotiation_service.analyze_negotiation(
        asking_price=1500000,
        estimated_value=1200000,
        market_median=1200000,
        market_p25=1120000,
        market_p75=1280000,
        comparable_count=8
    )
    assert res.buyer_leverage == "STRONG_BUYER_LEVERAGE"
    assert any("above central evidence benchmark" in tp for tp in res.talking_points)


def test_negotiation_without_asking_price():
    """Without asking price, service still provides statistical benchmarks."""
    res = negotiation_service.analyze_negotiation(
        asking_price=None,
        estimated_value=1100000,
        market_median=1120000,
        market_p25=1050000,
        market_p75=1180000,
        comparable_count=5
    )
    assert res.asking_price is None
    assert res.negotiation_gap is None
    assert res.evidence_supported_target > 0
    assert res.aggressive_target < res.evidence_supported_target


def test_negotiation_sparse_market_fallback():
    """Fallback when market median is unavailable."""
    res = negotiation_service.analyze_negotiation(
        asking_price=800000,
        estimated_value=750000,
        model_interval_low=700000,
        model_interval_high=800000,
        market_median=None,
        comparable_count=0
    )
    assert res.evidence_supported_target == 750000.0
    assert res.aggressive_target <= 750000.0
    assert res.conservative_target >= 750000.0
