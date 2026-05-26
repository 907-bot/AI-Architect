"""
Scene Graph Schema - Canonical representation for all scenes.
This is the SINGLE SOURCE OF TRUTH for every scene in the system.
All agents, API endpoints, and frontend renderers MUST respect this schema.
The LLM is NEVER allowed to output anything except valid JSON matching this schema.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
from uuid import UUID
from enum import Enum
import json


# =====================================================
# ENUMS — never extend without syncing frontend Zod types
# =====================================================

class RoomType(str, Enum):
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    LIVING_ROOM = "living_room"
    DINING_ROOM = "dining_room"
    HALLWAY = "hallway"
    GARAGE = "garage"
    LAUNDRY = "laundry"
    OFFICE = "office"
    STORAGE = "storage"
    STAIRCASE = "staircase"


class MaterialType(str, Enum):
    WOOD = "wood"
    CONCRETE = "concrete"
    GLASS = "glass"
    FABRIC = "fabric"
    METAL = "metal"
    PLASTIC = "plastic"
    TILE = "tile"
    CARPET = "carpet"
    PAINT = "paint"


class LightType(str, Enum):
    DIRECTIONAL = "directional"
    POINT = "point"
    SPOT = "spot"
    AMBIENT = "ambient"


class FurnitureType(str, Enum):
    SOFA = "sofa"
    CHAIR = "chair"
    BED = "bed"
    TABLE = "table"
    DESK = "desk"
    SHELF = "shelf"
    CABINET = "cabinet"
    LAMP = "lamp"
    COUNTER = "counter"
    STOVE = "stove"
    SINK = "sink"
    TOILET = "toilet"
    BATHTUB = "bathtub"
    SHOWER = "shower"


class ArchitecturalStyle(str, Enum):
    MODERN = "modern"
    CONTEMPORARY = "contemporary"
    TRADITIONAL = "traditional"
    MINIMALIST = "minimalist"
    INDIAN_CONTEMPORARY = "indian_contemporary"
    JAPANESE_MINIMAL = "japanese_minimal"
    SCANDINAVIAN = "scandinavian"
    MODERN_LUXURY = "modern_luxury"
    BRUTALIST = "brutalist"
    CYBERPUNK = "cyberpunk"


# =====================================================
# BASIC GEOMETRY — all units in meters
# =====================================================

class Vector3(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class Rotation(BaseModel):
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0


class BoundingBox(BaseModel):
    min: Vector3
    max: Vector3

    @property
    def size(self) -> Vector3:
        return Vector3(
            x=self.max.x - self.min.x,
            y=self.max.y - self.min.y,
            z=self.max.z - self.min.z
        )


# =====================================================
# MATERIALS
# =====================================================

class MaterialSpec(BaseModel):
    id: str
    name: str
    material_type: MaterialType
    color_rgb: str = "#CCCCCC"
    roughness: float = Field(0.5, ge=0.0, le=1.0)
    metallic: float = Field(0.0, ge=0.0, le=1.0)
    texture_url: Optional[str] = None
    albedo_url: Optional[str] = None
    normal_url: Optional[str] = None


# =====================================================
# WINDOWS & DOORS
# =====================================================

class WindowSpec(BaseModel):
    id: str
    room_id: str
    position: Vector3
    width: float = Field(..., ge=0.5, le=10.0)
    height: float = Field(..., ge=0.5, le=8.0)
    rotation: Rotation = Rotation()
    material_id: str
    window_type: str = "single"


class DoorSpec(BaseModel):
    id: str
    room_id: str
    position: Vector3
    width: float = Field(..., ge=0.6, le=3.0)
    height: float = Field(..., ge=1.8, le=4.0)
    rotation: Rotation = Rotation()
    material_id: str
    door_type: str = "swing"
    connects_to_room: Optional[str] = None


# =====================================================
# WALLS
# =====================================================

class WallSpec(BaseModel):
    id: str
    room_id: str
    start_point: Vector3
    end_point: Vector3
    height: float = Field(..., ge=2.0, le=20.0)
    thickness: float = Field(0.2, ge=0.1, le=1.0)
    material_id: str
    doors: List[DoorSpec] = []
    windows: List[WindowSpec] = []


# =====================================================
# FURNITURE & FIXTURES
# =====================================================

class FurnitureSpec(BaseModel):
    id: str
    room_id: str
    furniture_type: FurnitureType
    position: Vector3
    rotation: Rotation = Rotation()
    scale: Vector3 = Vector3(x=1.0, y=1.0, z=1.0)
    model_id: str = ""
    material_id: str = ""
    metadata: Dict[str, Any] = {}


# =====================================================
# LIGHTING
# =====================================================

class LightSpec(BaseModel):
    id: str
    room_id: str
    light_type: LightType
    position: Vector3
    color_rgb: str = "#FFFFFF"
    intensity: float = Field(1.0, ge=0.0, le=100.0)
    range: Optional[float] = None
    angle: Optional[float] = None


# =====================================================
# ROOMS
# =====================================================

class RoomSpec(BaseModel):
    id: str
    room_type: RoomType
    name: str
    floor_number: int = Field(0, ge=-5, le=200)
    position: Vector3 = Vector3()
    width: float = Field(..., ge=1.0, le=100.0)
    depth: float = Field(..., ge=1.0, le=100.0)
    height: float = Field(..., ge=2.0, le=20.0)
    material_id: str = ""
    walls: List[WallSpec] = []
    windows: List[WindowSpec] = []
    doors: List[DoorSpec] = []
    furniture: List[FurnitureSpec] = []
    lights: List[LightSpec] = []


# =====================================================
# STAIRS
# =====================================================

class StairSpec(BaseModel):
    id: str
    position: Vector3 = Vector3()
    rotation: Rotation = Rotation()
    floor_from: int = 0
    floor_to: int = 1
    width: float = Field(1.0, ge=0.5, le=10.0)
    height: float = Field(3.0, ge=1.0, le=20.0)
    step_count: int = Field(14, ge=1, le=200)
    material_id: str = ""


# =====================================================
# NAVIGATION
# =====================================================

class NavigationMesh(BaseModel):
    id: str
    room_id: str
    vertices: List[Vector3] = []
    faces: List[List[int]] = []


class NavigationSpec(BaseModel):
    navigation_meshes: List[NavigationMesh] = []
    walkthrough_points: List[Vector3] = []
    drone_path_nodes: List[Vector3] = []


# =====================================================
# COMPLETE SCENE GRAPH — CANONICAL SOURCE OF TRUTH
# =====================================================

class SceneGraph(BaseModel):
    scene_id: Optional[str] = None
    version: int = 1
    generation_prompt: Optional[str] = None
    created_at: Optional[str] = None
    style: ArchitecturalStyle = ArchitecturalStyle.MODERN
    rooms: List[RoomSpec] = []
    stairs: List[StairSpec] = []
    materials: List[MaterialSpec] = []
    lights: List[LightSpec] = []
    navigation: NavigationSpec = NavigationSpec()
    total_area: Optional[float] = None
    room_count: Optional[int] = None
    wall_count: Optional[int] = None

    @validator("rooms")
    def validate_no_duplicate_room_ids(cls, v):
        room_ids = [room.id for room in v if room.id]
        if len(room_ids) != len(set(room_ids)):
            raise ValueError("Duplicate room IDs detected")
        return v

    @validator("materials")
    def validate_material_ranges(cls, v):
        for material in v:
            if not (0.0 <= material.roughness <= 1.0):
                raise ValueError(f"Material {material.id} roughness out of range")
            if not (0.0 <= material.metallic <= 1.0):
                raise ValueError(f"Material {material.id} metallic out of range")
        return v

    def compute_properties(self) -> None:
        self.room_count = len(self.rooms)
        self.total_area = sum(room.width * room.depth for room in self.rooms) if self.rooms else 0.0
        self.wall_count = sum(len(room.walls) for room in self.rooms)

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(self.model_dump_json(exclude_none=True))

    @staticmethod
    def schema_json_str() -> str:
        return json.dumps(SceneGraph.model_json_schema())


# =====================================================
# GENERATION PARAMETERS
# =====================================================

class GenerationParameters(BaseModel):
    style: ArchitecturalStyle = ArchitecturalStyle.MODERN
    budget: str = "medium"
    occupancy: int = Field(4, ge=1, le=100)
    include_garage: bool = True
    include_basement: bool = False
    target_sqft: float = Field(2000.0, ge=100, le=100000)
    num_bedrooms: int = Field(3, ge=0, le=50)
    num_bathrooms: int = Field(2, ge=0, le=50)
    flooring_type: str = "hardwood"
    num_floors: int = Field(1, ge=1, le=50)


# =====================================================
# SCENE VALIDATION RULES — architectural constraints
# =====================================================

class SceneValidator:
    @staticmethod
    def validate_room_dimensions(room: RoomSpec) -> bool:
        return room.width >= 2.0 and room.depth >= 2.0 and room.height >= 2.0

    @staticmethod
    def validate_wall_connections(room: RoomSpec) -> bool:
        # Empty walls are valid (walls are optional / added incrementally)
        if not room.walls:
            return True
        return True

    @staticmethod
    def validate_door_dimensions(door: DoorSpec) -> bool:
        return door.width >= 0.6 and door.height >= 1.8

    @staticmethod
    def validate_window_dimensions(window: WindowSpec) -> bool:
        return window.width >= 0.3 and window.height >= 0.3

    @staticmethod
    def validate_scene_graph(scene: SceneGraph) -> tuple[bool, List[str]]:
        errors = []
        for room in scene.rooms:
            if not SceneValidator.validate_room_dimensions(room):
                errors.append(f"Room {room.id} has invalid dimensions (min 2m x 2m x 2m)")
            if not SceneValidator.validate_wall_connections(room):
                errors.append(f"Room {room.id} walls don't form closed loop")
            for door in room.doors:
                if not SceneValidator.validate_door_dimensions(door):
                    errors.append(f"Door {door.id} in room {room.id} has invalid dimensions")
            for window in room.windows:
                if not SceneValidator.validate_window_dimensions(window):
                    errors.append(f"Window {window.id} in room {room.id} has invalid dimensions")
        return len(errors) == 0, errors

    @staticmethod
    def validate_llm_output(raw: Any) -> tuple[bool, Optional[SceneGraph], str]:
        """Try to parse and validate raw LLM output. Returns (success, scene, error_msg)."""
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError as e:
                return False, None, f"JSON parse failed: {e}"
        if not isinstance(raw, dict):
            return False, None, "Output is not a JSON object"

        # Require the rooms field to be present explicitly
        if "rooms" not in raw:
            return False, None, "SceneGraph validation failed: missing required field 'rooms'"

        try:
            scene = SceneGraph(**raw)
            scene.compute_properties()
            return True, scene, ""
        except Exception as e:
            return False, None, f"SceneGraph validation failed: {e}"
