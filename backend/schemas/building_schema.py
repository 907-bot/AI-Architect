"""
backend/schemas/building_schema.py
Pydantic v2 models for the building generation pipeline.
"""

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal


class PoolConfig(BaseModel):
    enabled: bool = True
    width: float = Field(default=12.0, ge=4.0, le=30.0)
    length: float = Field(default=6.0,  ge=3.0, le=20.0)
    depth: float  = Field(default=1.8,  ge=1.0, le=3.0)


class GarageConfig(BaseModel):
    enabled: bool = True
    capacity: int = Field(default=2, ge=1, le=10)


class FloorConfig(BaseModel):
    level: int
    height: float = 3.2
    rooms: int = 4


class BuildingSchema(BaseModel):
    building_type: Literal["apartment", "villa", "office", "hotel", "warehouse"] = "apartment"
    floors: int         = Field(default=3, ge=1, le=30)
    width: float        = Field(default=20.0, ge=8.0, le=100.0)
    depth: float        = Field(default=15.0, ge=8.0, le=100.0)
    floor_height: float = Field(default=3.2, ge=2.4, le=6.0)
    style: Literal["modern", "classical", "industrial"] = "modern"
    roof_style: Literal["flat", "pitched", "dome"] = "flat"
    balconies: bool     = True
    pool: Optional[PoolConfig]    = None
    garage: Optional[GarageConfig] = None
    floor_data: List[FloorConfig] = []
    seed: int = 42

    @model_validator(mode="after")
    def fill_floor_data(self):
        if not self.floor_data:
            self.floor_data = [FloorConfig(level=i + 1) for i in range(self.floors)]
        return self

    model_config = {"extra": "ignore"}
