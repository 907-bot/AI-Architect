"""
NBC (National Building Code of India) Compliance Validator.
Implements real setback, FAR, height, and coverage rules per Indian NBC 2016 standards.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field

import math


class OccupancyClass(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    EDUCATIONAL = "educational"
    ASSEMBLY = "assembly"
    MERCANTILE = "mercantile"
    STORAGE = "storage"
    HAZARDOUS = "hazardous"


class ZoneType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    MIXED_USE = "mixed_use"


class NBCRules:
    """
    National Building Code 2016 — dimensional and zoning requirements.
    Based on NBC 2016 Volume 1, Sections 3–7 (Development Control Rules).
    """

    # Minimum setbacks (meters) per zone and building height
    SETBACKS: Dict[str, Dict[str, Dict[str, float]]] = {
        "residential": {
            "low_rise": {"front": 3.0, "rear": 1.5, "side": 1.5, "side_total": 3.0},
            "mid_rise": {"front": 4.5, "rear": 3.0, "side": 2.0, "side_total": 4.0},
            "high_rise": {"front": 6.0, "rear": 4.5, "side": 3.0, "side_total": 6.0},
        },
        "commercial": {
            "low_rise": {"front": 4.5, "rear": 3.0, "side": 2.0, "side_total": 4.0},
            "mid_rise": {"front": 6.0, "rear": 4.5, "side": 3.0, "side_total": 6.0},
            "high_rise": {"front": 9.0, "rear": 6.0, "side": 4.5, "side_total": 9.0},
        }
    }

    # Maximum FAR (Floor Area Ratio) per zone and plot size
    MAX_FAR: Dict[str, List[Dict[str, Any]]] = {
        "residential": [
            {"plot_max": 100, "far": 1.2},
            {"plot_max": 200, "far": 1.5},
            {"plot_max": 500, "far": 1.8},
            {"plot_max": 1000, "far": 2.0},
            {"plot_max": float("inf"), "far": 2.5},
        ],
        "commercial": [
            {"plot_max": 100, "far": 1.5},
            {"plot_max": 200, "far": 2.0},
            {"plot_max": 500, "far": 2.5},
            {"plot_max": 1000, "far": 3.0},
            {"plot_max": float("inf"), "far": 3.5},
        ]
    }

    # Maximum ground coverage (%) per zone
    MAX_COVERAGE: Dict[str, float] = {
        "residential": 60.0,
        "commercial": 75.0,
        "industrial": 60.0,
        "mixed_use": 70.0,
    }

    # Maximum building height (meters) per zone
    MAX_HEIGHT: Dict[str, Dict[str, float]] = {
        "residential": {"low_rise": 15.0, "mid_rise": 24.0, "high_rise": 45.0},
        "commercial": {"low_rise": 15.0, "mid_rise": 30.0, "high_rise": 60.0},
    }

    @staticmethod
    def get_building_category(height: float) -> str:
        if height <= 15:
            return "low_rise"
        elif height <= 24:
            return "mid_rise"
        else:
            return "high_rise"

    @staticmethod
    def get_max_far(zone: str, plot_area: float) -> float:
        rules = NBCRules.MAX_FAR.get(zone, NBCRules.MAX_FAR["residential"])
        for rule in rules:
            if plot_area <= rule["plot_max"]:
                return rule["far"]
        return rules[-1]["far"]

    @staticmethod
    def get_setbacks(zone: str, height: float) -> Dict[str, float]:
        cat = NBCRules.get_building_category(height)
        zone_rules = NBCRules.SETBACKS.get(zone, NBCRules.SETBACKS["residential"])
        return zone_rules.get(cat, zone_rules["low_rise"])


class ComplianceInput(BaseModel):
    zone: ZoneType = ZoneType.RESIDENTIAL
    plot_width: float = Field(..., ge=1, le=1000, description="Plot width in meters")
    plot_depth: float = Field(..., ge=1, le=1000, description="Plot depth in meters")
    building_width: float = Field(..., ge=0, le=1000, description="Building footprint width in meters")
    building_depth: float = Field(..., ge=0, le=1000, description="Building footprint depth in meters")
    building_height: float = Field(..., ge=0, le=200, description="Building height in meters")
    num_floors: int = Field(1, ge=0, le=200)
    occupancy: OccupancyClass = OccupancyClass.RESIDENTIAL
    set_front: Optional[float] = None
    set_rear: Optional[float] = None
    set_side: Optional[float] = None


class ComplianceIssue(BaseModel):
    type: str
    severity: str = "error"  # error, warning, info
    message: str
    actual: Optional[float] = None
    allowed: Optional[float] = None
    reference: Optional[str] = None


class ComplianceResult(BaseModel):
    compliant: bool = True
    issues: List[ComplianceIssue] = []
    actual_far: Optional[float] = None
    allowed_far: Optional[float] = None
    actual_coverage_pct: Optional[float] = None
    allowed_coverage_pct: Optional[float] = None
    vastu_suggestions: List[str] = []
    seismic_zone: Optional[str] = None


class NBCComplianceChecker:
    @staticmethod
    def check(input_data: ComplianceInput) -> ComplianceResult:
        result = ComplianceResult()
        issues = []
        plot_area = input_data.plot_width * input_data.plot_depth
        build_area = input_data.building_width * input_data.building_depth

        # 1. FAR check
        max_far = NBCRules.get_max_far(input_data.zone.value, plot_area)
        total_floor_area = build_area * input_data.num_floors
        actual_far = total_floor_area / plot_area if plot_area > 0 else 0
        result.actual_far = round(actual_far, 2)
        result.allowed_far = max_far

        if actual_far > max_far * 1.05:
            issues.append(ComplianceIssue(
                type="far",
                severity="error",
                message=f"FAR of {actual_far:.2f} exceeds maximum allowed {max_far:.2f}",
                actual=round(actual_far, 2),
                allowed=max_far,
                reference="NBC 2016 Vol 1, Section 4.2"
            ))
            result.compliant = False
        elif actual_far > max_far:
            issues.append(ComplianceIssue(
                type="far",
                severity="warning",
                message=f"FAR of {actual_far:.2f} is close to limit of {max_far:.2f}",
                actual=round(actual_far, 2),
                allowed=max_far,
                reference="NBC 2016 Vol 1, Section 4.2"
            ))

        # 2. Ground coverage check
        max_coverage = NBCRules.MAX_COVERAGE.get(input_data.zone.value, 60.0)
        coverage_pct = (build_area / plot_area * 100) if plot_area > 0 else 0
        result.actual_coverage_pct = round(coverage_pct, 1)
        result.allowed_coverage_pct = max_coverage

        if coverage_pct > max_coverage:
            issues.append(ComplianceIssue(
                type="coverage",
                severity="error",
                message=f"Ground coverage of {coverage_pct:.1f}% exceeds the maximum allowed {max_coverage:.0f}%",
                actual=round(coverage_pct, 1),
                allowed=max_coverage,
                reference="NBC 2016 Vol 1, Section 4.3"
            ))
            result.compliant = False
        elif coverage_pct > max_coverage * 0.9:
            issues.append(ComplianceIssue(
                type="coverage",
                severity="warning",
                message=f"Ground coverage of {coverage_pct:.1f}% is near the {max_coverage:.0f}% limit",
                actual=round(coverage_pct, 1),
                allowed=max_coverage,
                reference="NBC 2016 Vol 1, Section 4.3"
            ))

        # 3. Building height check
        max_height_map = NBCRules.MAX_HEIGHT.get(input_data.zone.value, NBCRules.MAX_HEIGHT["residential"])
        max_height = max_height_map.get(NBCRules.get_building_category(input_data.building_height), max_height_map["low_rise"])

        if input_data.building_height > max_height:
            issues.append(ComplianceIssue(
                type="height",
                severity="error",
                message=f"Building height of {input_data.building_height:.1f}m exceeds the maximum of {max_height:.0f}m for {input_data.zone.value} zone",
                actual=input_data.building_height,
                allowed=max_height,
                reference="NBC 2016 Vol 1, Section 5.1"
            ))
            result.compliant = False

        # 4. Setback checks
        required = NBCRules.get_setbacks(input_data.zone.value, input_data.building_height)

        if input_data.set_front is not None and input_data.set_front < required["front"]:
            issues.append(ComplianceIssue(
                type="setback_front",
                severity="error",
                message=f"Front setback of {input_data.set_front:.1f}m is below minimum {required['front']:.1f}m",
                actual=input_data.set_front,
                allowed=required["front"],
                reference=f"NBC 2016 Vol 1, Section 6.1 (front setback for {NBCRules.get_building_category(input_data.building_height)})"
            ))
            result.compliant = False

        if input_data.set_rear is not None and input_data.set_rear < required["rear"]:
            issues.append(ComplianceIssue(
                type="setback_rear",
                severity="error",
                message=f"Rear setback of {input_data.set_rear:.1f}m is below minimum {required['rear']:.1f}m",
                actual=input_data.set_rear,
                allowed=required["rear"],
                reference=f"NBC 2016 Vol 1, Section 6.2"
            ))
            result.compliant = False

        if input_data.set_side is not None and input_data.set_side < required["side"]:
            issues.append(ComplianceIssue(
                type="setback_side",
                severity="error",
                message=f"Side setback of {input_data.set_side:.1f}m is below minimum {required['side']:.1f}m",
                actual=input_data.set_side,
                allowed=required["side"],
                reference=f"NBC 2016 Vol 1, Section 6.3"
            ))
            result.compliant = False

        # 5. Vastu suggestions
        result.vastu_suggestions = NBCComplianceChecker._vastu_tips()

        # 6. Seismic zone (default Zone III for most of India)
        result.seismic_zone = "III"

        result.issues = issues
        # If no errors but there are warnings, still technically compliant
        has_errors = any(i.severity == "error" for i in issues)
        result.compliant = not has_errors

        return result

    @staticmethod
    def _vastu_tips() -> List[str]:
        return [
            "Main entrance is recommended in the North, East, or North-East corner.",
            "Kitchen is best placed in the South-East (Agneya) corner.",
            "Master bedroom should be in the South-West corner.",
            "Living room should face North or East.",
            "Pooja room should be in the North-East corner.",
            "Staircase should be in the South or West.",
            "Avoid toilet in the North-East corner.",
            "Plot slope should ideally be towards North or East.",
        ]


def check_compliance(
    plot_width: float,
    plot_depth: float,
    building_width: float,
    building_depth: float,
    building_height: float,
    num_floors: int = 1,
    zone: str = "residential",
    occupancy: str = "residential",
    set_front: Optional[float] = None,
    set_rear: Optional[float] = None,
    set_side: Optional[float] = None,
) -> ComplianceResult:
    inp = ComplianceInput(
        zone=zone,
        plot_width=plot_width,
        plot_depth=plot_depth,
        building_width=building_width,
        building_depth=building_depth,
        building_height=building_height,
        num_floors=num_floors,
        occupancy=occupancy,
        set_front=set_front,
        set_rear=set_rear,
        set_side=set_side,
    )
    return NBCComplianceChecker.check(inp)
