"""
Asset Library — furniture, materials, HDRIs, vegetation, decor.
Provides deterministic asset assignments based on design style and room type.
"""
from typing import Dict, Any, List, Optional
from backend.models.canonical_scene import DesignStyle


# =====================================================
# PBR MATERIAL LIBRARY
# =====================================================

PBR_MATERIALS: Dict[str, Dict[str, Any]] = {
    "oak_wood": {
        "name": "Oak Wood",
        "type": "wood",
        "color": "#B88A44",
        "roughness": 0.6,
        "metallic": 0.0,
        "albedo_url": "https://polyhaven.com/a/wood_floor_01",
        "normal_url": "https://polyhaven.com/a/wood_floor_01_nor",
        "roughness_url": "https://polyhaven.com/a/wood_floor_01_rough",
        "tags": ["wood", "floor", "natural"],
    },
    "white_marble": {
        "name": "White Marble",
        "type": "stone",
        "color": "#E8E0D8",
        "roughness": 0.1,
        "metallic": 0.0,
        "albedo_url": "https://polyhaven.com/a/marble_01",
        "normal_url": "https://polyhaven.com/a/marble_01_nor",
        "tags": ["stone", "luxury", "floor"],
    },
    "polished_concrete": {
        "name": "Polished Concrete",
        "type": "concrete",
        "color": "#8B8B8B",
        "roughness": 0.3,
        "metallic": 0.0,
        "albedo_url": "https://polyhaven.com/a/concrete_01",
        "normal_url": "https://polyhaven.com/a/concrete_01_nor",
        "tags": ["concrete", "industrial", "floor"],
    },
    "brushed_steel": {
        "name": "Brushed Steel",
        "type": "metal",
        "color": "#A8A8A8",
        "roughness": 0.3,
        "metallic": 0.9,
        "albedo_url": "https://polyhaven.com/a/metal_01",
        "normal_url": "https://polyhaven.com/a/metal_01_nor",
        "tags": ["metal", "industrial", "accent"],
    },
    "clear_glass": {
        "name": "Clear Glass",
        "type": "glass",
        "color": "#D4E8F0",
        "roughness": 0.0,
        "metallic": 0.1,
        "albedo_url": "https://polyhaven.com/a/glass_01",
        "tags": ["glass", "window", "transparent"],
    },
    "white_plaster": {
        "name": "White Plaster",
        "type": "plaster",
        "color": "#F5F5F0",
        "roughness": 0.9,
        "metallic": 0.0,
        "albedo_url": "https://polyhaven.com/a/plaster_01",
        "normal_url": "https://polyhaven.com/a/plaster_01_nor",
        "tags": ["wall", "interior", "plaster"],
    },
    "grey_fabric": {
        "name": "Grey Fabric",
        "type": "fabric",
        "color": "#A8A8A8",
        "roughness": 0.95,
        "metallic": 0.0,
        "tags": ["fabric", "furniture", "soft"],
    },
    "red_brick": {
        "name": "Red Brick",
        "type": "brick",
        "color": "#B85A3A",
        "roughness": 0.85,
        "metallic": 0.0,
        "albedo_url": "https://polyhaven.com/a/brick_01",
        "normal_url": "https://polyhaven.com/a/brick_01_nor",
        "tags": ["brick", "exterior", "wall"],
    },
    "cedar_wood": {
        "name": "Cedar Wood Siding",
        "type": "wood",
        "color": "#8B5A2B",
        "roughness": 0.7,
        "metallic": 0.0,
        "albedo_url": "https://polyhaven.com/a/wood_siding_01",
        "normal_url": "https://polyhaven.com/a/wood_siding_01_nor",
        "tags": ["wood", "exterior", "siding"],
    },
    "terracotta_tile": {
        "name": "Terracotta Tile",
        "type": "tile",
        "color": "#C86848",
        "roughness": 0.5,
        "metallic": 0.0,
        "albedo_url": "https://polyhaven.com/a/tile_01",
        "normal_url": "https://polyhaven.com/a/tile_01_nor",
        "tags": ["tile", "floor", "roof"],
    },
}


# =====================================================
# FURNITURE LIBRARY
# =====================================================

FURNITURE_LIBRARY: Dict[str, Dict[str, Any]] = {
    "sofa_modern": {
        "name": "Modern Sofa",
        "type": "sofa",
        "style_tags": ["modern", "contemporary", "minimalist"],
        "dimensions": {"width": 2.0, "depth": 0.8, "height": 0.7},
        "model_url": "https://models.readyplayer.me/sofa_modern.glb",
    },
    "sofa_scandinavian": {
        "name": "Scandinavian Sofa",
        "type": "sofa",
        "style_tags": ["scandinavian"],
        "dimensions": {"width": 2.2, "depth": 0.85, "height": 0.65},
        "model_url": "https://models.readyplayer.me/sofa_scandi.glb",
    },
    "bed_queen": {
        "name": "Queen Bed",
        "type": "bed",
        "style_tags": ["modern", "scandinavian", "contemporary"],
        "dimensions": {"width": 1.6, "depth": 2.0, "height": 0.5},
        "model_url": "https://models.readyplayer.me/bed_queen.glb",
    },
    "dining_table_6": {
        "name": "6-Seater Dining Table",
        "type": "table",
        "style_tags": ["modern", "traditional", "indian_contemporary"],
        "dimensions": {"width": 1.8, "depth": 0.9, "height": 0.75},
        "model_url": "https://models.readyplayer.me/dining_table_6.glb",
    },
    "desk_modern": {
        "name": "Modern Desk",
        "type": "desk",
        "style_tags": ["modern", "minimalist", "scandinavian"],
        "dimensions": {"width": 1.2, "depth": 0.6, "height": 0.75},
        "model_url": "https://models.readyplayer.me/desk_modern.glb",
    },
    "bookshelf_tall": {
        "name": "Tall Bookshelf",
        "type": "shelf",
        "style_tags": ["modern", "traditional", "scandinavian"],
        "dimensions": {"width": 0.8, "depth": 0.3, "height": 1.8},
        "model_url": "https://models.readyplayer.me/bookshelf_tall.glb",
    },
    "lamp_floor_modern": {
        "name": "Modern Floor Lamp",
        "type": "lamp",
        "style_tags": ["modern", "contemporary", "minimalist"],
        "dimensions": {"width": 0.3, "depth": 0.3, "height": 1.5},
        "model_url": "https://models.readyplayer.me/lamp_floor.glb",
    },
    "coffee_table": {
        "name": "Coffee Table",
        "type": "table",
        "style_tags": ["modern", "scandinavian", "minimalist"],
        "dimensions": {"width": 1.0, "depth": 0.6, "height": 0.4},
        "model_url": "https://models.readyplayer.me/coffee_table.glb",
    },
    "japanese_tatami": {
        "name": "Tatami Mat",
        "type": "flooring",
        "style_tags": ["japanese_minimal"],
        "dimensions": {"width": 1.8, "depth": 0.9, "height": 0.05},
        "model_url": "https://models.readyplayer.me/tatami.glb",
    },
}


# =====================================================
# HDRI ENVIRONMENT MAPS
# =====================================================

HDRI_ENVIRONMENTS: Dict[str, Dict[str, str]] = {
    "sunset_park": {
        "name": "Sunset Park",
        "url": "https://polyhaven.com/a/sunset_park_01",
        "type": "outdoor",
        "time": "golden_hour",
    },
    "overcast_day": {
        "name": "Overcast Day",
        "url": "https://polyhaven.com/a/overcast_day",
        "type": "outdoor",
        "time": "day",
    },
    "night_city": {
        "name": "Night City",
        "url": "https://polyhaven.com/a/night_city_01",
        "type": "outdoor",
        "time": "night",
    },
    "golden_hour": {
        "name": "Golden Hour",
        "url": "https://polyhaven.com/a/golden_hour_01",
        "type": "outdoor",
        "time": "golden_hour",
    },
    "overcast_industrial": {
        "name": "Industrial Overcast",
        "url": "https://polyhaven.com/a/industrial_01",
        "type": "outdoor",
        "time": "day",
    },
    "zen_garden": {
        "name": "Zen Garden",
        "url": "https://polyhaven.com/a/garden_01",
        "type": "outdoor",
        "time": "morning",
    },
    "tropical_modern": {
        "name": "Tropical Resort",
        "url": "https://polyhaven.com/a/tropical_01",
        "type": "outdoor",
        "time": "day",
    },
    "mineral": {
        "name": "Mineral Landscape",
        "url": "https://polyhaven.com/a/mineral_01",
        "type": "outdoor",
        "time": "day",
    },
    "courtyard": {
        "name": "Traditional Courtyard",
        "url": "https://polyhaven.com/a/courtyard_01",
        "type": "outdoor",
        "time": "afternoon",
    },
}


# =====================================================
# ASSET RESOLVER
# =====================================================

class AssetResolver:
    """Resolves asset assignments based on scene configuration."""

    @staticmethod
    def resolve_materials(design_style: DesignStyle) -> List[Dict[str, Any]]:
        from backend.services.style_engine import get_materials_for_style
        return get_materials_for_style(design_style)

    @staticmethod
    def resolve_furniture(
        style: DesignStyle,
        room_type: str,
        count: int = 3
    ) -> List[Dict[str, Any]]:
        """Resolve furniture items for a room based on style."""
        style_val = style.value
        candidates = []
        for fid, fdata in FURNITURE_LIBRARY.items():
            tags = fdata.get("style_tags", [])
            if style_val in tags or "modern" in tags:
                candidates.append({"id": fid, **fdata})
        if not candidates:
            candidates = [{"id": k, **v} for k, v in FURNITURE_LIBRARY.items()]
        return candidates[:count]

    @staticmethod
    def resolve_hdri(environment_name: str) -> Optional[Dict[str, str]]:
        return HDRI_ENVIRONMENTS.get(environment_name)

    @staticmethod
    def resolve_material_by_name(name: str) -> Optional[Dict[str, Any]]:
        return PBR_MATERIALS.get(name)

    @staticmethod
    def list_all_materials() -> List[Dict[str, Any]]:
        return [
            {"id": k, **v} for k, v in PBR_MATERIALS.items()
        ]

    @staticmethod
    def list_all_furniture() -> List[Dict[str, Any]]:
        return [
            {"id": k, **v} for k, v in FURNITURE_LIBRARY.items()
        ]

    @staticmethod
    def list_all_hdris() -> List[Dict[str, str]]:
        return [
            {"id": k, **v} for k, v in HDRI_ENVIRONMENTS.items()
        ]


asset_resolver = AssetResolver()
