"""
Compliance API routes — NBC building code validation
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import structlog

from backend.services.compliance import (
    check_compliance, ComplianceResult, ZoneType, OccupancyClass
)

log = structlog.get_logger()
router = APIRouter()


class ComplianceRequest(BaseModel):
    plot_width: float
    plot_depth: float
    building_width: float
    building_depth: float
    building_height: float = 3.0
    num_floors: int = 1
    zone: str = "residential"
    occupancy: str = "residential"
    set_front: Optional[float] = None
    set_rear: Optional[float] = None
    set_side: Optional[float] = None


@router.post("/check", response_model=ComplianceResult)
async def check_building_compliance(request: ComplianceRequest):
    """
    Validate building design against NBC 2016 building code.
    Checks FAR, ground coverage, height, setbacks, and provides Vastu tips.
    """
    log.info(
        "compliance_check",
        plot=f"{request.plot_width}x{request.plot_depth}",
        building=f"{request.building_width}x{request.building_depth}x{request.building_height}",
        floors=request.num_floors,
    )

    try:
        result = check_compliance(
            plot_width=request.plot_width,
            plot_depth=request.plot_depth,
            building_width=request.building_width,
            building_depth=request.building_depth,
            building_height=request.building_height,
            num_floors=request.num_floors,
            zone=request.zone,
            occupancy=request.occupancy,
            set_front=request.set_front,
            set_rear=request.set_rear,
            set_side=request.set_side,
        )
        return result
    except Exception as e:
        log.error("compliance_check_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance check failed: {str(e)}",
        )
