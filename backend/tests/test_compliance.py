"""
Tests for NBC compliance validator
"""
import pytest
from backend.services.compliance import check_compliance, ComplianceResult


def test_compliance_valid():
    """A building within limits should pass compliance"""
    result = check_compliance(
        plot_width=20, plot_depth=30,
        building_width=12, building_depth=15,
        building_height=10, num_floors=2,
        zone="residential",
    )
    assert isinstance(result, ComplianceResult)
    # Plot area = 600, building footprint = 180, coverage = 30%, far = 360/600 = 0.6
    # 30% < 60% coverage, 0.6 < 1.8 FAR for 600sqm plot
    assert result.compliant
    assert result.actual_coverage_pct is not None
    assert result.actual_far is not None
    assert len(result.vastu_suggestions) > 0


def test_compliance_far_exceeded():
    """Very dense building should fail FAR"""
    result = check_compliance(
        plot_width=10, plot_depth=10,
        building_width=9, building_depth=9,
        building_height=15, num_floors=5,
        zone="residential",
    )
    # Plot=100sqm, build=81sqm, coverage=81% > 60%, total floor=405,
    # FAR = 4.05 > 1.2 (max for plot <100sqm)
    assert not result.compliant
    far_errors = [i for i in result.issues if i.type == "far"]
    coverage_errors = [i for i in result.issues if i.type == "coverage"]
    assert len(far_errors) > 0
    assert len(coverage_errors) > 0


def test_compliance_height_exceeded():
    """Very tall building should fail height check"""
    result = check_compliance(
        plot_width=30, plot_depth=40,
        building_width=15, building_depth=15,
        building_height=50, num_floors=12,
        zone="residential",
    )
    assert not result.compliant
    height_errors = [i for i in result.issues if i.type == "height"]
    assert len(height_errors) > 0


def test_compliance_setbacks():
    """Building too close to property lines should fail"""
    result = check_compliance(
        plot_width=20, plot_depth=30,
        building_width=18, building_depth=28,
        building_height=10, num_floors=2,
        zone="residential",
        set_front=1.0, set_rear=0.5, set_side=0.5,
    )
    # Required: front=3.0, rear=1.5, side=1.5
    assert not result.compliant
    setback_types = {i.type for i in result.issues}
    assert "setback_front" in setback_types
    assert "setback_rear" in setback_types
    assert "setback_side" in setback_types


def test_compliance_vastu_suggestions():
    """Vastu suggestions should always be present"""
    result = check_compliance(
        plot_width=15, plot_depth=20,
        building_width=8, building_depth=10,
        building_height=9, num_floors=1,
    )
    assert len(result.vastu_suggestions) >= 5
    assert any("North" in s for s in result.vastu_suggestions)
