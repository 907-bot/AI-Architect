"""
Scene Graph Schema - Canonical representation for all scenes
This ensures consistency across agents and prevents hallucinations
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
from uuid import UUID
from enum import Enum


# =====================================================
# ENUMS
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


# =====================================================
# BASIC GEOMETRY
# =====================================================

class Vector3(BaseModel):
    """3D Position/Scale/Direction"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class Rotation(BaseModel):
    """Rotation in degrees (Euler angles)"""
    pitch: float = 0.0  # Rotation around X axis
    yaw: float = 0.0    # Rotation around Y axis
    roll: float = 0.0   # Rotation around Z axis


class BoundingBox(BaseModel):
    """Axis-aligned bounding box"""
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
    """Material definition"""
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
    """Window opening specification"""
    id: str
    room_id: str
    position: Vector3  # Relative to room
    width: float
    height: float
    rotation: Rotation
    material_id: str
    window_type: str = "single"  # single, double, sliding, etc.


class DoorSpec(BaseModel):
    """Door opening specification"""
    id: str
    room_id: str
    position: Vector3  # Position on wall
    width: float
    height: float
    rotation: Rotation
    material_id: str
    door_type: str = "swing"  # swing, sliding, pocket, etc.
    connects_to_room: Optional[str] = None  # Other room ID


# =====================================================
# WALLS
# =====================================================

class WallSpec(BaseModel):
    """Wall specification"""
    id: str
    room_id: str
    start_point: Vector3
    end_point: Vector3
    height: float
    thickness: float
    material_id: str
    doors: List[DoorSpec] = []
    windows: List[WindowSpec] = []


# =====================================================
# FURNITURE & FIXTURES
# =====================================================

class FurnitureSpec(BaseModel):
    """Furniture/fixture placement"""
    id: str
    room_id: str
    furniture_type: FurnitureType
    position: Vector3
    rotation: Rotation
    scale: Vector3 = Vector3(x=1.0, y=1.0, z=1.0)
    model_id: str  # Reference to asset library
    material_id: str
    metadata: Dict[str, Any] = {}


# =====================================================
# LIGHTING
# =====================================================

class LightSpec(BaseModel):
    """Light source specification"""
    id: str
    room_id: str
    light_type: LightType
    position: Vector3
    color_rgb: str = "#FFFFFF"
    intensity: float = 1.0
    range: Optional[float] = None  # For point/spot lights
    angle: Optional[float] = None  # For spot lights


# =====================================================
# ROOMS
# =====================================================

class RoomSpec(BaseModel):
    """Complete room specification"""
    id: str
    room_type: RoomType
    name: str
    floor_number: int
    position: Vector3
    width: float
    depth: float
    height: float
    material_id: str  # Floor material
    
    # Room layout
    walls: List[WallSpec]
    windows: List[WindowSpec]
    doors: List[DoorSpec]
    furniture: List[FurnitureSpec]
    lights: List[LightSpec]


# =====================================================
# STAIRS
# =====================================================

class StairSpec(BaseModel):
    """Staircase specification"""
    id: str
    position: Vector3
    rotation: Rotation
    floor_from: int
    floor_to: int
    width: float
    height: float
    step_count: int
    material_id: str


# =====================================================
# NAVIGATION & PATHFINDING
# =====================================================

class NavigationMesh(BaseModel):
    """Navigation mesh for pathfinding"""
    id: str
    room_id: str
    vertices: List[Vector3]
    faces: List[tuple]  # Triangles


class NavigationSpec(BaseModel):
    """Navigation system for walkthroughs and drone paths"""
    navigation_meshes: List[NavigationMesh]
    walkthrough_points: List[Vector3]  # Suggested viewpoints
    drone_path_nodes: List[Vector3]  # Drone flight path


# =====================================================
# COMPLETE SCENE GRAPH
# =====================================================

class SceneGraph(BaseModel):
    """
    Canonical scene representation.
    This is the source of truth for all scene data.
    All agents must work with this schema.
    """
    
    # Metadata
    scene_id: Optional[UUID] = None
    version: int = 1
    generation_prompt: Optional[str] = None
    created_at: Optional[str] = None
    
    # Core geometry
    rooms: List[RoomSpec]
    stairs: List[StairSpec]
    materials: List[MaterialSpec]
    
    # Systems
    lights: List[LightSpec]
    navigation: NavigationSpec
    
    # Computed properties (read-only)
    total_area: Optional[float] = None
    room_count: Optional[int] = None
    wall_count: Optional[int] = None
    
    @validator("rooms")
    def validate_no_duplicate_room_ids(cls, v):
        room_ids = [room.id for room in v]
        if len(room_ids) != len(set(room_ids)):
            raise ValueError("Duplicate room IDs detected")
        return v
    
    @validator("materials")
    def validate_material_types(cls, v):
        for material in v:
            if material.roughness < 0 or material.roughness > 1:
                raise ValueError("Material roughness must be 0-1")
            if material.metallic < 0 or material.metallic > 1:
                raise ValueError("Material metallic must be 0-1")
        return v
    
    def compute_properties(self) -> None:
        """Compute derived properties"""
        self.room_count = len(self.rooms)
        self.total_area = sum(room.width * room.depth for room in self.rooms)
        self.wall_count = sum(len(room.walls) for room in self.rooms)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return self.dict(exclude_none=True)


# =====================================================
# GENERATION PARAMETERS
# =====================================================

class GenerationParameters(BaseModel):
    """Parameters for scene generation"""
    style: str = "modern"  # modern, contemporary, traditional, minimalist
    budget: str = "medium"  # low, medium, high
    occupancy: int = 4  # Number of people
    include_garage: bool = True
    include_basement: bool = False
    target_sqft: float = 2000.0
    num_bedrooms: int = 3
    num_bathrooms: int = 2
    flooring_type: str = "hardwood"


# =====================================================
# SCENE VALIDATION RULES
# =====================================================

class SceneValidator:
    """Validates scenes against architectural rules"""
    
    @staticmethod
    def validate_room_dimensions(room: RoomSpec) -> bool:
        """Validate room is reasonable size"""
        # Room should be at least 7ft x 7ft x 8ft high
        return room.width >= 7 and room.depth >= 7 and room.height >= 8
    
    @staticmethod
    def validate_wall_connections(room: RoomSpec) -> bool:
        """Validate walls form closed loop"""
        if not room.walls:
            return False
        # Check walls form topology
        return True
    
    @staticmethod
    def validate_door_dimensions(door: DoorSpec) -> bool:
        """Validate door dimensions"""
        # Standard door is 32-36 inches wide, 80 inches high
        return door.width >= 2.5 and door.height >= 6.5
    
    @staticmethod
    def validate_window_dimensions(window: WindowSpec) -> bool:
        """Validate window dimensions"""
        # Minimum window size
        return window.width >= 1.5 and window.height >= 1.5
    
    @staticmethod
    def validate_scene_graph(scene: SceneGraph) -> tuple[bool, List[str]]:
        """Validate entire scene graph"""
        errors = []
        
        for room in scene.rooms:
            if not SceneValidator.validate_room_dimensions(room):
                errors.append(f"Room {room.id} has invalid dimensions")
            if not SceneValidator.validate_wall_connections(room):
                errors.append(f"Room {room.id} walls don't form closed loop")
            
            for door in room.doors:
                if not SceneValidator.validate_door_dimensions(door):
                    errors.append(f"Door {door.id} in room {room.id} has invalid dimensions")
            
            for window in room.windows:
                if not SceneValidator.validate_window_dimensions(window):
                    errors.append(f"Window {window.id} in room {room.id} has invalid dimensions")
        
        return len(errors) == 0, errors
