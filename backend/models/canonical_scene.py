"""
Canonical Scene Schema — universal source of truth for ALL output modes.
This schema replaces ad-hoc scene generation with a structured format that
drives every renderer: Three.js, Blender, Unreal, IFC, CAD, etc.

The AI NEVER generates geometry directly. It fills this schema.
Deterministic converters turn this into scenes for each output mode.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any, Literal
from enum import Enum
import json


# =====================================================
# DESIGN SYSTEM — Governs ALL visual output
# =====================================================

class DesignStyle(str, Enum):
    JAPANESE_MINIMAL = "japanese_minimal"
    SCANDINAVIAN = "scandinavian"
    MODERN_LUXURY = "modern_luxury"
    BRUTALIST = "brutalist"
    INDIAN_CONTEMPORARY = "indian_contemporary"
    CYBERPUNK = "cyberpunk"
    MODERN = "modern"
    CONTEMPORARY = "contemporary"
    TRADITIONAL = "traditional"
    MINIMALIST = "minimalist"


class RoofType(str, Enum):
    FLAT = "flat"
    GABLE = "gable"
    HIP = "hip"
    SHED = "shed"
    MANSARD = "mansard"
    DOME = "dome"
    PYRAMID = "pyramid"
    BUTTERFLY = "butterfly"
    SAWTOOTH = "sawtooth"
    BARREL = "barrel"


class WindowStyle(str, Enum):
    CASEMENT = "casement"
    SLIDING = "sliding"
    AWNING = "awning"
    PICTURE = "picture"
    BAY = "bay"
    BOW = "bow"
    LOUVERED = "louvered"
    SKYLIGHT = "skylight"
    CLERESTORY = "clerestory"
    ARCHED = "arched"


class FlooringType(str, Enum):
    HARDWOOD = "hardwood"
    TILE = "tile"
    CARPET = "carpet"
    LAMINATE = "laminate"
    VINYL = "vinyl"
    MARBLE = "marble"
    GRANITE = "granite"
    TERRAZZO = "terrazzo"
    POLISHED_CONCRETE = "polished_concrete"
    BAMBOO = "bamboo"


class DesignSystem(BaseModel):
    """Controls every visual aspect of a scene based on chosen style."""
    style: DesignStyle = DesignStyle.MODERN
    roof_type: RoofType = RoofType.FLAT
    window_style: WindowStyle = WindowStyle.CASEMENT
    flooring_type: FlooringType = FlooringType.HARDWOOD
    wall_color_palette: List[str] = ["#F5F5F0", "#E8E0D8", "#F0EDE5"]
    accent_color: str = "#7C93C3"
    trim_color: str = "#FFFFFF"
    roof_color: str = "#5C5C5C"
    window_frame_color: str = "#2C2C2C"
    roof_pitch: float = Field(30.0, ge=0.0, le=90.0)
    window_density: float = Field(0.4, ge=0.0, le=1.0)
    furniture_density: float = Field(0.3, ge=0.0, le=1.0)
    lighting_warmth: float = Field(0.5, ge=0.0, le=1.0)
    exterior_finish: str = "plaster"
    interior_finish: str = "paint"
    landscaping_style: str = "minimal"
    hdri_environment: str = "sunset_park"


# =====================================================
# ARCHITECTURAL PROPERTIES
# =====================================================

class SiteContext(BaseModel):
    """Plot and location information."""
    latitude: float = 19.0760
    longitude: float = 72.8777
    plot_width_m: float = Field(20.0, ge=1.0)
    plot_depth_m: float = Field(30.0, ge=1.0)
    orientation_deg: float = Field(0.0, ge=0.0, le=360.0)
    set_front_m: float = Field(3.0, ge=0.0)
    set_back_m: float = Field(3.0, ge=0.0)
    set_side_m: float = Field(1.5, ge=0.0)
    max_floors: int = Field(3, ge=1, le=50)
    soil_type: str = "medium"
    seismic_zone: str = "III"


class FacadeSpec(BaseModel):
    """Exterior facade configuration."""
    id: str
    wall_id: str
    finish_material_id: str = ""
    cladding_material_id: Optional[str] = None
    color_rgb: str = "#F5F5F0"
    has_columns: bool = False
    column_positions: List[float] = []
    fenestration_ratio: float = Field(0.3, ge=0.0, le=0.9)


class LandscapeSpec(BaseModel):
    """Exterior landscaping elements."""
    has_garden: bool = True
    has_lawn: bool = True
    has_patio: bool = False
    has_driveway: bool = True
    has_pool: bool = False
    vegetation_density: float = Field(0.3, ge=0.0, le=1.0)
    tree_positions: List[Dict[str, float]] = []
    plant_species: List[str] = []


class EnergySpec(BaseModel):
    """Energy and sustainability parameters."""
    solar_orientation_deg: float = 180.0
    has_solar_panels: bool = False
    solar_panel_area_m2: float = 0.0
    insulation_rating: str = "standard"
    glazing_type: str = "double"
    has_green_roof: bool = False


class ConstructionSpec(BaseModel):
    """Construction details for BIM/CAD export."""
    foundation_type: str = "raft"
    frame_material: str = "reinforced_concrete"
    wall_construction: str = "brick_cavity"
    slab_thickness_mm: float = 150.0
    roof_construction: str = "rcc_slab"
    insulation_material: str = "mineral_wool"


# =====================================================
# EXPANDED BUILDING ELEMENTS
# =====================================================

class ColumnSpec(BaseModel):
    id: str
    room_id: str
    position: Dict[str, float]
    width_m: float = 0.3
    depth_m: float = 0.3
    height_m: float = 3.0
    material_id: str = ""


class BeamSpec(BaseModel):
    id: str
    room_id: str
    start_position: Dict[str, float]
    end_position: Dict[str, float]
    width_m: float = 0.3
    depth_m: float = 0.45
    material_id: str = ""


class StairSpec(BaseModel):
    id: str
    position: Dict[str, float] = {"x": 0, "y": 0, "z": 0}
    rotation: Dict[str, float] = {"pitch": 0, "yaw": 0, "roll": 0}
    floor_from: int = 0
    floor_to: int = 1
    width: float = Field(1.0, ge=0.5, le=10.0)
    height: float = Field(3.0, ge=1.0, le=20.0)
    step_count: int = Field(14, ge=1, le=200)
    stair_type: str = "straight"  # straight, l_shaped, u_shaped, spiral, curved
    material_id: str = ""
    has_handrail: bool = True
    has_railing: bool = True


class RailingSpec(BaseModel):
    id: str
    element_id: str
    height_m: float = 1.0
    baluster_spacing_m: float = 0.15
    material_id: str = ""


class CeilingSpec(BaseModel):
    id: str
    room_id: str
    height_m: float = 3.0
    type: str = "flat"  # flat, tray, coffered, cathedral, vaulted
    material_id: str = ""
    has_crown_molding: bool = False
    has_false_ceiling: bool = False


class HVACSpec(BaseModel):
    type: str = "split"  # split, central, ductless, window
    zones: List[str] = []
    efficiency_rating: str = "5_star"


class PlumbingSpec(BaseModel):
    water_supply: str = "municipal"
    sewage_type: str = "municipal"
    has_water_tank: bool = True
    water_tank_capacity_l: float = 1000.0
    has_septic_tank: bool = False


class ElectricalSpec(BaseModel):
    main_voltage: str = "230V"
    phase: str = "single"
    has_backup_generator: bool = False
    has_inverter: bool = True
    lighting_load_w: float = 5000.0


# =====================================================
# COMPLETE CANONICAL SCENE
# =====================================================

class CanonicalScene(BaseModel):
    """
    Universal scene format.
    This is the SINGLE SOURCE OF TRUTH.
    Every output mode (Three.js, Blender, Unreal, IFC, CAD, etc.)
    is derived from this schema deterministically.
    """
    scene_id: Optional[str] = None
    version: str = "2.0"
    name: str = "Untitled Scene"
    description: str = ""

    # Design system (controls ALL visual output)
    design_system: DesignSystem = DesignSystem()

    # Generation metadata
    generation_prompt: Optional[str] = None
    created_at: Optional[str] = None
    output_mode: str = "fast_preview"
    # fast_preview | architectural_concept | realistic_visualization |
    # technical_floorplan | construction_bim | xr_export |
    # fabrication_cad | marketing_walkthrough

    # Existing scene graph data (reused from SceneGraph)
    rooms: List[Dict[str, Any]] = []
    walls: List[Dict[str, Any]] = []
    windows: List[Dict[str, Any]] = []
    doors: List[Dict[str, Any]] = []
    furniture: List[Dict[str, Any]] = []
    materials: List[Dict[str, Any]] = []
    lights: List[Dict[str, Any]] = []

    # NEW: Expanded architectural elements
    stairs: List[StairSpec] = []
    columns: List[ColumnSpec] = []
    beams: List[BeamSpec] = []
    railings: List[RailingSpec] = []
    ceilings: List[CeilingSpec] = []
    facades: List[FacadeSpec] = []

    # Site and context
    site: SiteContext = SiteContext()
    landscape: LandscapeSpec = LandscapeSpec()

    # Engineering systems
    hvac: HVACSpec = HVACSpec()
    plumbing: PlumbingSpec = PlumbingSpec()
    electrical: ElectricalSpec = ElectricalSpec()
    energy: EnergySpec = EnergySpec()
    construction: ConstructionSpec = ConstructionSpec()

    # Navigation
    navigation_meshes: List[Dict[str, Any]] = []
    walkthrough_points: List[Dict[str, float]] = []
    drone_path_nodes: List[Dict[str, float]] = []

    # Computed properties
    total_area_m2: Optional[float] = None
    total_volume_m3: Optional[float] = None
    room_count: Optional[int] = None
    floor_count: Optional[int] = None

    def compute_properties(self):
        self.room_count = len(self.rooms)
        floors = set(r.get("floor_number", 0) for r in self.rooms)
        self.floor_count = len(floors) if floors else 1
        self.total_area_m2 = sum(
            r.get("width", 0) * r.get("depth", 0) for r in self.rooms
        )
        self.total_volume_m3 = sum(
            r.get("width", 0) * r.get("depth", 0) * r.get("height", 3)
            for r in self.rooms
        )

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(self.model_dump_json(exclude_none=True))

    @staticmethod
    def from_scene_graph(sg_dict: Dict[str, Any]) -> "CanonicalScene":
        """Upgrade from legacy SceneGraph format."""
        scene = CanonicalScene()
        scene.rooms = sg_dict.get("rooms", [])
        scene.walls = []
        for r in scene.rooms:
            scene.walls.extend(r.get("walls", []))
        scene.windows = []
        for r in scene.rooms:
            scene.windows.extend(r.get("windows", []))
        scene.doors = []
        for r in scene.rooms:
            scene.doors.extend(r.get("doors", []))
        scene.furniture = []
        for r in scene.rooms:
            scene.furniture.extend(r.get("furniture", []))
        scene.lights = []
        for r in scene.rooms:
            scene.lights.extend(r.get("lights", []))
        scene.materials = sg_dict.get("materials", [])

        style_str = sg_dict.get("style", "modern")
        try:
            scene.design_system.style = DesignStyle(style_str)
        except ValueError:
            pass

        nav = sg_dict.get("navigation", {})
        scene.navigation_meshes = nav.get("navigation_meshes", [])
        scene.walkthrough_points = nav.get("walkthrough_points", [])
        scene.drone_path_nodes = nav.get("drone_path_nodes", [])
        scene.generation_prompt = sg_dict.get("generation_prompt")
        scene.compute_properties()
        return scene
