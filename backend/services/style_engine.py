"""
Style Engine — translates design styles into concrete geometry,
material, lighting, and landscaping parameters.
Every style produces deterministic, high-quality outputs.
"""
from typing import Dict, Any, List, Tuple
from backend.models.canonical_scene import (
    DesignStyle, RoofType, WindowStyle, FlooringType, DesignSystem
)


# =====================================================
# STYLE DEFINITIONS
# =====================================================

StyleConfig = Dict[str, Any]

STYLE_REGISTRY: Dict[DesignStyle, StyleConfig] = {
    DesignStyle.JAPANESE_MINIMAL: {
        "roof_type": RoofType.GABLE,
        "window_style": WindowStyle.CASEMENT,
        "flooring_type": FlooringType.BAMBOO,
        "wall_colors": ["#F5F0E8", "#EDE4D4", "#E8DDCC"],
        "accent_color": "#8B4513",
        "trim_color": "#2C1810",
        "roof_color": "#4A4A4A",
        "window_frame_color": "#1A1A1A",
        "roof_pitch": 40.0,
        "window_density": 0.3,
        "furniture_density": 0.15,
        "lighting_warmth": 0.7,
        "exterior_finish": "wood_siding",
        "interior_finish": "plaster",
        "landscaping_style": "zen_garden",
        "hdri_environment": "golden_hour",
        "description": "Clean lines, natural materials, open spaces",
        "materials": {
            "floor": {"type": "wood", "color": "#C4A882", "roughness": 0.6, "metallic": 0.0},
            "wall": {"type": "paint", "color": "#F5F0E8", "roughness": 0.9, "metallic": 0.0},
            "accent": {"type": "wood", "color": "#8B4513", "roughness": 0.7, "metallic": 0.0},
            "roof": {"type": "tile", "color": "#4A4A4A", "roughness": 0.8, "metallic": 0.0},
        },
        "lighting": {
            "ambient_intensity": 0.4,
            "warmth_kelvin": 2700,
            "uses_shoji": True,
            "uses_floor_lamps": True,
        },
        "furniture_style": "japanese_antique",
        "has_tatami": True,
        "has_sliding_doors": True,
        "has_engawa": True,
    },
    DesignStyle.SCANDINAVIAN: {
        "roof_type": RoofType.GABLE,
        "window_style": WindowStyle.PICTURE,
        "flooring_type": FlooringType.HARDWOOD,
        "wall_colors": ["#FFFFFF", "#F8F8F8", "#F0F0F0"],
        "accent_color": "#C9845E",
        "trim_color": "#FFFFFF",
        "roof_color": "#3D3D3D",
        "window_frame_color": "#FFFFFF",
        "roof_pitch": 35.0,
        "window_density": 0.6,
        "furniture_density": 0.3,
        "lighting_warmth": 0.8,
        "exterior_finish": "wood_cladding",
        "interior_finish": "paint",
        "landscaping_style": "minimal_nordic",
        "hdri_environment": "overcast_day",
        "description": "Light, cozy, functional with natural elements",
        "materials": {
            "floor": {"type": "wood", "color": "#D4B896", "roughness": 0.5, "metallic": 0.0},
            "wall": {"type": "paint", "color": "#FFFFFF", "roughness": 0.85, "metallic": 0.0},
            "accent": {"type": "fabric", "color": "#C9845E", "roughness": 0.9, "metallic": 0.0},
            "roof": {"type": "tile", "color": "#3D3D3D", "roughness": 0.8, "metallic": 0.0},
        },
        "lighting": {
            "ambient_intensity": 0.6,
            "warmth_kelvin": 3000,
            "uses_pendant_lights": True,
            "uses_floor_lamps": True,
        },
        "furniture_style": "mid_century",
        "has_wood_stove": True,
        "has_skylights": True,
        "has_mudroom": True,
    },
    DesignStyle.MODERN_LUXURY: {
        "roof_type": RoofType.FLAT,
        "window_style": WindowStyle.SLIDING,
        "flooring_type": FlooringType.MARBLE,
        "wall_colors": ["#FFFFFF", "#FAFAFA", "#F2F0F0"],
        "accent_color": "#C0A080",
        "trim_color": "#1A1A1A",
        "roof_color": "#808080",
        "window_frame_color": "#1A1A1A",
        "roof_pitch": 5.0,
        "window_density": 0.7,
        "furniture_density": 0.4,
        "lighting_warmth": 0.5,
        "exterior_finish": "glass_and_steel",
        "interior_finish": "plaster",
        "landscaping_style": "tropical_modern",
        "hdri_environment": "sunset_park",
        "description": "Premium materials, open plan, dramatic spaces",
        "materials": {
            "floor": {"type": "stone", "color": "#E8E0D8", "roughness": 0.1, "metallic": 0.0},
            "wall": {"type": "paint", "color": "#FFFFFF", "roughness": 0.8, "metallic": 0.0},
            "accent": {"type": "metal", "color": "#C0A080", "roughness": 0.3, "metallic": 0.8},
            "roof": {"type": "membrane", "color": "#808080", "roughness": 0.5, "metallic": 0.0},
        },
        "lighting": {
            "ambient_intensity": 0.5,
            "warmth_kelvin": 3500,
            "uses_chandeliers": True,
            "uses_cove_lighting": True,
        },
        "furniture_style": "contemporary_luxury",
        "has_wine_cellar": True,
        "has_home_theater": True,
        "has_infinity_pool": True,
    },
    DesignStyle.BRUTALIST: {
        "roof_type": RoofType.FLAT,
        "window_style": WindowStyle.PICTURE,
        "flooring_type": FlooringType.POLISHED_CONCRETE,
        "wall_colors": ["#8B8B8B", "#7A7A7A", "#696969"],
        "accent_color": "#FF4500",
        "trim_color": "#4A4A4A",
        "roof_color": "#5A5A5A",
        "window_frame_color": "#2C2C2C",
        "roof_pitch": 0.0,
        "window_density": 0.3,
        "furniture_density": 0.2,
        "lighting_warmth": 0.3,
        "exterior_finish": "exposed_concrete",
        "interior_finish": "exposed_concrete",
        "landscaping_style": "mineral",
        "hdri_environment": "overcast_industrial",
        "description": "Raw concrete, monumental forms, honest materials",
        "materials": {
            "floor": {"type": "concrete", "color": "#8B8B8B", "roughness": 0.9, "metallic": 0.0},
            "wall": {"type": "concrete", "color": "#7A7A7A", "roughness": 0.95, "metallic": 0.0},
            "accent": {"type": "metal", "color": "#FF4500", "roughness": 0.5, "metallic": 0.6},
            "roof": {"type": "concrete", "color": "#5A5A5A", "roughness": 0.9, "metallic": 0.0},
        },
        "lighting": {
            "ambient_intensity": 0.3,
            "warmth_kelvin": 4000,
            "uses_industrial_lights": True,
            "uses_spotlights": True,
        },
        "furniture_style": "industrial",
        "has_roof_garden": True,
        "has_double_height": True,
    },
    DesignStyle.INDIAN_CONTEMPORARY: {
        "roof_type": RoofType.FLAT,
        "window_style": WindowStyle.CASEMENT,
        "flooring_type": FlooringType.MARBLE,
        "wall_colors": ["#F5E6D0", "#E8D5B7", "#D4C4A8"],
        "accent_color": "#B22222",
        "trim_color": "#8B6914",
        "roof_color": "#6B6B6B",
        "window_frame_color": "#3D2B1F",
        "roof_pitch": 5.0,
        "window_density": 0.4,
        "furniture_density": 0.35,
        "lighting_warmth": 0.8,
        "exterior_finish": "plaster",
        "interior_finish": "paint",
        "landscaping_style": "courtyard",
        "hdri_environment": "golden_hour",
        "description": "Traditional Indian elements with modern planning",
        "materials": {
            "floor": {"type": "stone", "color": "#E8D5B7", "roughness": 0.3, "metallic": 0.0},
            "wall": {"type": "paint", "color": "#F5E6D0", "roughness": 0.85, "metallic": 0.0},
            "accent": {"type": "wood", "color": "#8B6914", "roughness": 0.6, "metallic": 0.0},
            "roof": {"type": "concrete", "color": "#6B6B6B", "roughness": 0.8, "metallic": 0.0},
        },
        "lighting": {
            "ambient_intensity": 0.6,
            "warmth_kelvin": 3000,
            "uses_lanterns": True,
            "uses_cove_lighting": True,
        },
        "furniture_style": "indian_contemporary",
        "has_courtyard": True,
        "has_jali": True,
        "has_veranda": True,
    },
    DesignStyle.CYBERPUNK: {
        "roof_type": RoofType.FLAT,
        "window_style": WindowStyle.SLIDING,
        "flooring_type": FlooringType.VINYL,
        "wall_colors": ["#1A1A2E", "#16213E", "#0F3460"],
        "accent_color": "#FF2E63",
        "trim_color": "#00FFFF",
        "roof_color": "#1A1A2E",
        "window_frame_color": "#00FFFF",
        "roof_pitch": 0.0,
        "window_density": 0.5,
        "furniture_density": 0.3,
        "lighting_warmth": 0.2,
        "exterior_finish": "metal_panels",
        "interior_finish": "metal_panels",
        "landscaping_style": "urban",
        "hdri_environment": "night_city",
        "description": "Neon-lit, high-tech, urban dystopian aesthetic",
        "materials": {
            "floor": {"type": "vinyl", "color": "#2A2A3E", "roughness": 0.3, "metallic": 0.4},
            "wall": {"type": "metal", "color": "#1A1A2E", "roughness": 0.4, "metallic": 0.7},
            "accent": {"type": "neon", "color": "#FF2E63", "roughness": 0.0, "metallic": 0.9},
            "roof": {"type": "metal", "color": "#1A1A2E", "roughness": 0.5, "metallic": 0.6},
        },
        "lighting": {
            "ambient_intensity": 0.2,
            "warmth_kelvin": 6000,
            "uses_neon_strips": True,
            "uses_led_panels": True,
        },
        "furniture_style": "hightech",
        "has_holographic_displays": True,
        "has_smart_glass": True,
        "has_vertical_garden": True,
    },
}


def get_style_config(style: DesignStyle) -> StyleConfig:
    """Get the full style configuration for a given design style."""
    if style in STYLE_REGISTRY:
        return STYLE_REGISTRY[style]
    return STYLE_REGISTRY[DesignStyle.MODERN]


def apply_style_to_design_system(style: DesignStyle) -> DesignSystem:
    """Apply a design style to create a complete DesignSystem."""
    cfg = get_style_config(style)
    palette = cfg.get("wall_colors", ["#F5F5F0", "#E8E0D8", "#F0EDE5"])
    return DesignSystem(
        style=style,
        roof_type=cfg.get("roof_type", RoofType.FLAT),
        window_style=cfg.get("window_style", WindowStyle.CASEMENT),
        flooring_type=cfg.get("flooring_type", FlooringType.HARDWOOD),
        wall_color_palette=palette,
        accent_color=cfg.get("accent_color", "#7C93C3"),
        trim_color=cfg.get("trim_color", "#FFFFFF"),
        roof_color=cfg.get("roof_color", "#5C5C5C"),
        window_frame_color=cfg.get("window_frame_color", "#2C2C2C"),
        roof_pitch=cfg.get("roof_pitch", 30.0),
        window_density=cfg.get("window_density", 0.4),
        furniture_density=cfg.get("furniture_density", 0.3),
        lighting_warmth=cfg.get("lighting_warmth", 0.5),
        exterior_finish=cfg.get("exterior_finish", "plaster"),
        interior_finish=cfg.get("interior_finish", "paint"),
        landscaping_style=cfg.get("landscaping_style", "minimal"),
        hdri_environment=cfg.get("hdri_environment", "sunset_park"),
    )


def get_materials_for_style(style: DesignStyle) -> List[Dict[str, Any]]:
    """Get material definitions for a given style."""
    cfg = get_style_config(style)
    mats = cfg.get("materials", {})
    return [
        {
            "id": f"{key}_{style.value}",
            "name": key.replace("_", " ").title(),
            "material_type": v["type"],
            "color_rgb": v["color"],
            "roughness": v["roughness"],
            "metallic": v["metallic"],
        }
        for key, v in mats.items()
    ]


def get_lighting_for_style(style: DesignStyle) -> List[Dict[str, Any]]:
    """Get lighting configuration for a given style."""
    cfg = get_style_config(style)
    lt = cfg.get("lighting", {})
    warmth = lt.get("warmth_kelvin", 3000)
    intensity = lt.get("ambient_intensity", 0.5)
    return [
        {
            "id": f"ambient_{style.value}",
            "light_type": "ambient",
            "intensity": intensity,
            "color_temperature_k": warmth,
        },
        {
            "id": f"sun_{style.value}",
            "light_type": "directional",
            "intensity": 1.0 - intensity * 0.5,
            "angle_deg": 45,
        },
    ]


def get_furniture_assignments(
    style: DesignStyle,
    rooms: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Get furniture placements for rooms based on style."""
    cfg = get_style_config(style)
    density = cfg.get("furniture_density", 0.3)
    furniture_style = cfg.get("furniture_style", "modern")
    assignments = []
    for room in rooms:
        room_type = room.get("room_type", "living_room")
        room_w = room.get("width", 5)
        room_d = room.get("depth", 5)
        rp = room.get("position", {"x": 0, "y": 0, "z": 0})
        items_for_room = room_furniture_map.get(room_type, [])
        count = max(1, int(len(items_for_room) * density))
        for i in range(count):
            frac = (i + 1) / (count + 1)
            assignments.append({
                "room_id": room.get("id", ""),
                "furniture_type": items_for_room[i % len(items_for_room)],
                "position": {
                    "x": rp.get("x", 0) - room_w / 2 + room_w * frac,
                    "y": rp.get("y", 0),
                    "z": rp.get("z", 0) - room_d / 2 + room_d * 0.3,
                },
                "furniture_style": furniture_style,
            })
    return assignments


room_furniture_map = {
    "living_room": ["sofa", "table", "chair", "shelf", "lamp"],
    "bedroom": ["bed", "desk", "chair", "cabinet", "lamp"],
    "kitchen": ["counter", "table", "chair", "cabinet", "stove"],
    "dining_room": ["table", "chair"],
    "office": ["desk", "chair", "shelf", "lamp"],
    "bathroom": ["sink", "toilet", "cabinet"],
}


def list_available_styles() -> List[Dict[str, Any]]:
    """List all available design styles with descriptions."""
    return [
        {
            "id": s.value,
            "name": s.name.replace("_", " ").title(),
            "description": STYLE_REGISTRY[s].get("description", ""),
            "landscaping": STYLE_REGISTRY[s].get("landscaping_style", ""),
            "hdri": STYLE_REGISTRY[s].get("hdri_environment", ""),
        }
        for s in DesignStyle
    ]
