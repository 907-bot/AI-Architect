"""
Asset Library MCP Server
Materials, textures, furniture catalog lookup.
"""
from fastmcp import FastMCP

mcp = FastMCP("asset-library-mcp")

# Built-in material catalog
MATERIALS = {
    "plaster_white":  {"name": "White Plaster",      "color": "#F5F5F0", "roughness": 0.8, "metallic": 0.0, "type": "matte"},
    "concrete":       {"name": "Concrete",            "color": "#9E9E9E", "roughness": 0.9, "metallic": 0.0, "type": "matte"},
    "concrete_dark":  {"name": "Dark Concrete",       "color": "#616161", "roughness": 0.85,"metallic": 0.0, "type": "matte"},
    "brick_red":      {"name": "Red Brick",           "color": "#B5451B", "roughness": 0.95,"metallic": 0.0, "type": "matte"},
    "glass_clear":    {"name": "Clear Glass",         "color": "#C8E6FF", "roughness": 0.05,"metallic": 0.0, "type": "glass", "transparent": True, "opacity": 0.15},
    "glass_tinted":   {"name": "Tinted Glass",        "color": "#78909C", "roughness": 0.05,"metallic": 0.0, "type": "glass", "transparent": True, "opacity": 0.4},
    "wood_pine":      {"name": "Pine Wood",           "color": "#D4A96A", "roughness": 0.75,"metallic": 0.0, "type": "wood"},
    "wood_oak":       {"name": "Oak Wood",            "color": "#8B6914", "roughness": 0.7, "metallic": 0.0, "type": "wood"},
    "marble_white":   {"name": "White Marble",        "color": "#F8F8F5", "roughness": 0.1, "metallic": 0.05,"type": "stone"},
    "steel_brushed":  {"name": "Brushed Steel",       "color": "#BDBDBD", "roughness": 0.3, "metallic": 0.9, "type": "metal"},
    "roof_tile":      {"name": "Clay Roof Tile",      "color": "#8D4E2A", "roughness": 0.9, "metallic": 0.0, "type": "ceramic"},
    "grass":          {"name": "Grass",               "color": "#4CAF50", "roughness": 1.0, "metallic": 0.0, "type": "organic"},
    "asphalt":        {"name": "Asphalt",             "color": "#424242", "roughness": 0.95,"metallic": 0.0, "type": "road"},
}

# Furniture catalog (placeholder URLs — replace with R2 hosted models)
FURNITURE = {
    "sofa_modern":    {"name": "Modern Sofa",        "category": "living", "width": 2.2, "depth": 0.9, "height": 0.85},
    "bed_king":       {"name": "King Bed",           "category": "bedroom","width": 2.0, "depth": 2.1, "height": 0.6},
    "desk_simple":    {"name": "Study Desk",         "category": "office", "width": 1.4, "depth": 0.7, "height": 0.76},
    "dining_table":   {"name": "Dining Table",       "category": "dining", "width": 1.8, "depth": 0.9, "height": 0.76},
    "kitchen_counter":{"name": "Kitchen Counter",    "category": "kitchen","width": 2.5, "depth": 0.6, "height": 0.9},
    "wardrobe":       {"name": "Wardrobe",           "category": "bedroom","width": 1.6, "depth": 0.6, "height": 2.2},
    "bathtub":        {"name": "Bathtub",            "category": "bathroom","width":1.7, "depth": 0.8, "height": 0.55},
    "toilet":         {"name": "Toilet",             "category": "bathroom","width":0.45,"depth": 0.7, "height": 0.85},
    "shower_cubicle": {"name": "Shower Cubicle",     "category": "bathroom","width":0.9, "depth": 0.9, "height": 2.2},
}


@mcp.tool()
def get_material(material_id: str) -> dict:
    """Get a material by ID."""
    mat = MATERIALS.get(material_id)
    if not mat:
        return {"error": f"Material '{material_id}' not found"}
    return {"id": material_id, **mat}


@mcp.tool()
def search_materials(query: str = "", material_type: str = "") -> dict:
    """Search materials by name or type."""
    results = []
    for mid, mat in MATERIALS.items():
        if query.lower() in mat["name"].lower() or material_type == mat.get("type", ""):
            results.append({"id": mid, **mat})
    return {"materials": results, "count": len(results)}


@mcp.tool()
def get_furniture(furniture_id: str) -> dict:
    """Get a furniture item by ID."""
    item = FURNITURE.get(furniture_id)
    if not item:
        return {"error": f"Furniture '{furniture_id}' not found"}
    return {"id": furniture_id, **item}


@mcp.tool()
def search_furniture(category: str = "") -> dict:
    """List furniture items, optionally filtered by category."""
    results = []
    for fid, item in FURNITURE.items():
        if not category or item["category"] == category:
            results.append({"id": fid, **item})
    return {"furniture": results, "count": len(results)}


@mcp.tool()
def suggest_materials_for_style(style: str) -> dict:
    """Suggest a curated material palette for an architectural style."""
    palettes = {
        "modern":      ["plaster_white", "concrete", "glass_clear", "steel_brushed"],
        "industrial":  ["concrete_dark", "steel_brushed", "asphalt", "glass_tinted"],
        "traditional": ["brick_red", "wood_oak", "marble_white", "roof_tile"],
        "minimal":     ["plaster_white", "marble_white", "glass_clear", "wood_pine"],
        "warm":        ["wood_pine", "brick_red", "grass", "roof_tile"],
    }
    ids = palettes.get(style.lower(), palettes["modern"])
    return {
        "style": style,
        "palette": [{"id": mid, **MATERIALS[mid]} for mid in ids if mid in MATERIALS],
    }


@mcp.tool()
def suggest_furniture_for_room(room_type: str) -> dict:
    """Suggest appropriate furniture for a room type."""
    suggestions = {
        "living room":  ["sofa_modern", "dining_table"],
        "bedroom":      ["bed_king", "wardrobe", "desk_simple"],
        "kitchen":      ["kitchen_counter", "dining_table"],
        "bathroom":     ["bathtub", "toilet", "shower_cubicle"],
        "office":       ["desk_simple"],
        "dining room":  ["dining_table"],
    }
    room_lower = room_type.lower()
    ids = suggestions.get(room_lower, [])
    return {
        "room_type": room_type,
        "furniture": [{"id": fid, **FURNITURE[fid]} for fid in ids if fid in FURNITURE],
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
