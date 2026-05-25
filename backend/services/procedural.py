"""Procedural Building Generator - Enhanced Version"""
import uuid
from typing import Dict, Any, List

# Enhanced PBR Materials with realistic properties
# c=color, r=roughness, m=metallic, o=opacity, t=transmission
MATERIALS = {
    # Walls
    "concrete": {"c": "#9d9d9d", "r": 0.85, "m": 0.0},
    "plaster_white": {"c": "#f5f5f0", "r": 0.75, "m": 0.0},
    "plaster_grey": {"c": "#e0e0e0", "r": 0.7, "m": 0.0},
    "brick_red": {"c": "#a0522d", "r": 0.8, "m": 0.0},
    "brick_dark": {"c": "#654321", "r": 0.75, "m": 0.0},
    "limestone": {"c": "#d9d0c1", "r": 0.75, "m": 0.0},
    
    # Windows
    "glass_clear": {"c": "#d0e8f0", "r": 0.1, "m": 0.0, "o": 0.15, "t": 0.85},
    "glass_tinted": {"c": "#405060", "r": 0.15, "m": 0.1, "o": 0.25, "t": 0.65},
    "frame_black": {"c": "#1a1a1a", "r": 0.3, "m": 0.7},
    "frame_white": {"c": "#f0f0f0", "r": 0.4, "m": 0.5},
    
    # Doors
    "wood_oak": {"c": "#8b5a2b", "r": 0.6, "m": 0.0},
    "wood_dark": {"c": "#4a3020", "r": 0.5, "m": 0.0},
    
    # Roofing  
    "roof_tiles": {"c": "#b22222", "r": 0.65, "m": 0.0},
    "roof_slate": {"c": "#4a4a4a", "r": 0.6, "m": 0.0},
    "roof_metal": {"c": "#708090", "r": 0.4, "m": 0.5},
    
    # Metal
    "metal_grey": {"c": "#707070", "r": 0.3, "m": 0.7},
    "metal_black": {"c": "#252525", "r": 0.25, "m": 0.8},
    
    # Landscape
    "grass": {"c": "#4a7c23", "r": 0.9, "m": 0.0},
    "patio_stone": {"c": "#a0a090", "r": 0.8, "m": 0.0},
}


def generate_detailed_building(
    btype: str = "house",
    style: str = "modern",
    floors: int = 2,
    plot_width: float = 20,
    plot_depth: float = 30,
    beds: int = 3,
    garage: bool = True,
    pool: bool = False,
    garden: bool = True,
    roof_style: str = "gable"
) -> Dict[str, Any]:
    """
    Generate detailed building with architectural elements
    
    Args:
        btype: house, villa, apartment, cabin
        style: modern, classical, minimalist, cottage
        floors: number of floors (1-3)
        plot_width: plot width in meters
        plot_depth: plot depth in meters  
        beds: number of bedrooms
        garage: include garage
        pool: include swimming pool
        garden: include landscaping
        roof_style: flat, gable, hip, mansard
    """
    
    # Scale for Three.js viewer (smaller for better visualization)
    scale = 0.4
    pw = plot_width * scale
    pd = plot_depth * scale
    floor_height = 3.0 * scale  # 3m per floor
    ceiling_height = 0.15  # Ceiling thickness
    
    meshes = []
    
    # Select materials based on style
    style_materials = {
        "modern": {"wall": "plaster_white", "roof": "roof_metal"},
        "classical": {"wall": "brick_red", "roof": "roof_tiles"},
        "minimalist": {"wall": "plaster_grey", "roof": "roof_slate"},
        "cottage": {"wall": "brick_dark", "roof": "roof_tiles"},
    }
    mats = style_materials.get(style, style_materials["modern"])
    wall_mat = mats["wall"]
    roof_mat = mats["roof"]
    
    # ========== 1. FOUNDATION ==========
    thickness = 0.25 * scale
    meshes.append({
        "id": f"foundation_{uuid.uuid4().hex[:4]}",
        "component_group": "Foundation",
        "type": "box",
        "position": [0, -thickness/2, 0],
        "scale": [pw, thickness, pd],
        "material_id": "concrete"
    })
    
    # ========== 2. FLOORS AND WALLS ==========
    for floor in range(floors):
        y_pos = floor * floor_height + floor_height/2 + 0.1
        
        # Main floor slab (intermediate)
        if floor > 0:
            meshes.append({
                "id": f"floor_slab_{floor}_{uuid.uuid4().hex[:4]}",
                "component_group": "Floor Slabs",
                "type": "box", 
                "position": [0, floor * floor_height + 0.015, 0],
                "scale": [pw * 0.92, 0.03, pd * 0.92],
                "material_id": "concrete"
            })
        
        # Exterior walls
        meshes.append({
            "id": f"exterior_wall_{floor}_{uuid.uuid4().hex[:4]}",
            "component_group": "Exterior",
            "type": "box",
            "position": [0, y_pos, 0],
            "scale": [pw * 0.96, floor_height - 0.05, pd * 0.96],
            "material_id": wall_mat
        })
    
    # ========== 3. WINDOWS WITH GLASS + FRAMES ==========
    num_windows = min(beds + 1, 5)  # More windows for more bedrooms
    win_width = pw * 0.2
    win_height = floor_height * 0.45
    win_depth = 0.015
    
    for floor in range(floors):
        base_y = floor * floor_height + floor_height * 0.25 + 0.12
        
        # Front windows
        for wi in range(num_windows):
            wx = (wi - (num_windows-1)/2) * pw * 0.22
            
            # Glass pane
            meshes.append({
                "id": f"window_glass_f{floor}_{wi}_{uuid.uuid4().hex[:4]}",
                "component_group": "Windows",
                "type": "box",
                "position": [wx, base_y, pd/2 - win_depth/2],
                "scale": [win_width, win_height, win_depth],
                "material_id": "glass_clear"
            })
            
            # Window frame
            meshes.append({
                "id": f"window_frame_f{floor}_{wi}_{uuid.uuid4().hex[:4]}",
                "component_group": "Windows", 
                "type": "box",
                "position": [wx, base_y, pd/2],
                "scale": [win_width * 1.08, win_height * 1.08, 0.012],
                "material_id": "frame_black"
            })
            
            # Back windows
            meshes.append({
                "id": f"window_glass_b{floor}_{wi}_{uuid.uuid4().hex[:4]}",
                "component_group": "Windows",
                "type": "box",
                "position": [wx, base_y, -pd/2 + win_depth/2],
                "scale": [win_width, win_height, win_depth],
                "material_id": "glass_clear"
            })
            
            # Side windows
            meshes.append({
                "id": f"window_glass_s{floor}_{wi}_{uuid.uuid4().hex[:4]}",
                "component_group": "Windows",
                "type": "box",
                "position": [pw/2 - win_depth/2, base_y, wx],
                "scale": [win_depth, win_height, win_width],
                "material_id": "glass_clear"
            })
    
    # ========== 4. ENTRANCE / DOOR ==========
    door_y = 0.11
    # Door panel with detail lines
    meshes.append({
        "id": f"door_panel_{uuid.uuid4().hex[:4]}",
        "component_group": "Entrance",
        "type": "box",
        "position": [0, door_y, pd/2 - 0.008],
        "scale": [0.1, 0.23, 0.015],
        "material_id": "wood_oak"
    })
    
    # Door frame
    meshes.append({
        "id": f"door_frame_{uuid.uuid4().hex[:4]}",
        "component_group": "Entrance",
        "type": "box",
        "position": [0, door_y + 0.01, pd/2],
        "scale": [0.13, 0.26, 0.012],
        "material_id": "frame_black"
    })
    
    # Entrance canopy
    meshes.append({
        "id": f"entrance_canopy_{uuid.uuid4().hex[:4]}",
        "component_group": "Entrance", 
        "type": "box",
        "position": [0, 0.3, pd/2 + 0.12],
        "scale": [0.18, 0.025, 0.12],
        "material_id": "metal_grey"
    })
    
    # ========== 5. ROOF ==========
    roof_y = floors * floor_height + 0.06
    
    if roof_style == "flat":
        # Flat roof with parapet
        meshes.append({
            "id": f"flat_roof_{uuid.uuid4().hex[:4]}",
            "component_group": "Roof",
            "type": "box",
            "position": [0, roof_y + 0.025, 0],
            "scale": [pw * 0.92, 0.05, pd * 0.92],
            "material_id": roof_mat
        })
        
    elif roof_style == "gable":
        # Main sloped roof
        meshes.append({
            "id": f"roof_slope_front_{uuid.uuid4().hex[:4]}",
            "component_group": "Roof",
            "type": "box",
            "position": [0, roof_y + 0.12, pd*0.48],
            "scale": [pw * 1.02, 0.12, pd * 0.08],
            "material_id": roof_mat
        })
        meshes.append({
            "id": f"roof_slope_back_{uuid.uuid4().hex[:4]}",
            "component_group": "Roof",
            "type": "box",
            "position": [0, roof_y + 0.12, -pd*0.48],
            "scale": [pw * 1.02, 0.12, pd * 0.08],
            "material_id": roof_mat
        })
        # Ridge
        meshes.append({
            "id": f"ridge_cap_{uuid.uuid4().hex[:4]}",
            "component_group": "Roof",
            "type": "box", 
            "position": [0, roof_y + 0.2, 0],
            "scale": [pw * 1.04, 0.025, 0.06],
            "material_id": roof_mat
        })
        
    elif roof_style == "hip":
        # Hip roof
        meshes.append({
            "id": f"hip_roof_{uuid.uuid4().hex[:4]}",
            "component_group": "Roof",
            "type": "box",
            "position": [0, roof_y + 0.15, 0],
            "scale": [pw * 0.98, 0.22, pd * 0.98],
            "material_id": roof_mat
        })
    
    # ========== 6. GARAGE ==========
    if garage:
        garage_x = -(pw + 0.35)
        garage_y = 0.15
        garage_z = -pd * 0.15
        
        meshes.append({
            "id": f"garage_structure_{uuid.uuid4().hex[:4]}",
            "component_group": "Garage",
            "type": "box",
            "position": [garage_x, garage_y, garage_z],
            "scale": [0.45, 0.28, 0.55],
            "material_id": wall_mat
        })
        
        # Garage door
        meshes.append({
            "id": f"garage_door_{uuid.uuid4().hex[:4]}",
            "component_group": "Garage", 
            "type": "box",
            "position": [garage_x, garage_y - 0.08, garage_z + 0.28],
            "scale": [0.32, 0.2, 0.015],
            "material_id": "metal_grey"
        })
    
    # ========== 7. POOL ==========
    if pool:
        pool_x = pw * 0.12
        pool_z = -pd * 0.38
        
        # Pool edge/concrete
        meshes.append({
            "id": f"pool_edge_{uuid.uuid4().hex[:4]}",
            "component_group": "Pool",
            "type": "box",
            "position": [pool_x, -0.035, pool_z],
            "scale": [0.65, 0.015, 0.45],
            "material_id": "patio_stone"
        })
        
        # Pool water
        meshes.append({
            "id": f"pool_water_{uuid.uuid4().hex[:4]}",
            "component_group": "Pool",
            "type": "box",
            "position": [pool_x, 0.0, pool_z],
            "scale": [0.58, 0.14, 0.38],
            "material_id": "glass_tinted"
        })
    
    # ========== 8. LANDSCAPING ==========
    if garden:
        # Main ground
        meshes.append({
            "id": f"landscape_ground_{uuid.uuid4().hex[:4]}",
            "component_group": "Landscape",
            "type": "box",
            "position": [0, -0.065, 0],
            "scale": [pw + 0.9, 0.025, pd + 1.0],
            "material_id": "grass"
        })
        
        # Patio area
        meshes.append({
            "id": f"patio_{uuid.uuid4().hex[:4]}", 
            "component_group": "Landscape",
            "type": "box",
            "position": [pw * 0.3, -0.055, pd/2 + 0.2],
            "scale": [0.35, 0.01, 0.25],
            "material_id": "patio_stone"
        })
    
    # ========== 9. FENCE / BOUNDARY ==========
    fence_height = 0.12
    
    # Front fence
    meshes.append({
        "id": f"fence_front_{uuid.uuid4().hex[:4]}",
        "component_group": "Boundary",
        "type": "box",
        "position": [0, fence_height/2, pd/2 + 0.06],
        "scale": [pw + 0.15, fence_height, 0.012],
        "material_id": "metal_black"
    })
    
    # Back fence  
    meshes.append({
        "id": f"fence_back_{uuid.uuid4().hex[:4]}",
        "component_group": "Boundary",
        "type": "box",
        "position": [0, fence_height/2, -pd/2 - 0.06],
        "scale": [pw + 0.15, fence_height, 0.012],
        "material_id": "metal_black"
    })
    
    # Left fence
    meshes.append({
        "id": f"fence_left_{uuid.uuid4().hex[:4]}",
        "component_group": "Boundary",
        "type": "box",
        "position": [-pw/2 - 0.06, fence_height/2, 0],
        "scale": [0.012, fence_height, pd + 0.12],
        "material_id": "metal_black"
    })
    
    # Right fence
    meshes.append({
        "id": f"fence_right_{uuid.uuid4().hex[:4]}",
        "component_group": "Boundary", 
        "type": "box",
        "position": [pw/2 + 0.06, fence_height/2, 0],
        "scale": [0.012, fence_height, pd + 0.12],
        "material_id": "metal_black"
    })
    
    # ========== 10. CHIMNEY ==========
    if style != "modern":
        meshes.append({
            "id": f"chimney_{uuid.uuid4().hex[:4]}",
            "component_group": "Chimney",
            "type": "box",
            "position": [pw * 0.35, roof_y + 0.28, pd * 0.3],
            "scale": [0.07, 0.18, 0.07],
            "material_id": "brick_dark"
        })
    
    # Build materials list — use 'id' key so frontend can find them without remapping
    materials_list = [
        {"id": k, "color_hex": v["c"], "roughness": v["r"], "metallic": v.get("m", 0.0),
         "opacity": v.get("o", 1.0), "transparent": "o" in v}
        for k, v in MATERIALS.items()
    ]
    
    return {
        "meshes": meshes,
        "materials": materials_list,
        "metadata": {
            "building_type": btype,
            "style": style,
            "floors": floors,
            "roof_style": roof_style,
            "plot_width": plot_width,
            "plot_depth": plot_depth,
            "total_elements": len(meshes)
        }
    }


# Main entry point for API
def generate_building(**kwargs) -> Dict[str, Any]:
    """Wrapper for API compatibility"""
    # Map color_scheme to a style
    color_to_style = {"red": "classical", "dark": "minimalist", "cream": "cottage", "white": "modern"}
    color_scheme = kwargs.get("color_scheme", "white")
    style = kwargs.get("style", color_to_style.get(color_scheme, "modern"))

    return generate_detailed_building(
        btype=kwargs.get("btype", kwargs.get("prompt", "house")),
        style=style,
        floors=kwargs.get("floors", 2),
        plot_width=kwargs.get("pw", kwargs.get("plot_width", 20)),
        plot_depth=kwargs.get("pd", kwargs.get("plot_depth", 30)),
        beds=kwargs.get("beds", 3),
        garage=kwargs.get("garage", True),
        pool=kwargs.get("pool", False),
        garden=kwargs.get("garden", True),
        roof_style=kwargs.get("roof_style", "gable")
    )


# Legacy wrapper
def gen_building(**kwargs) -> Dict[str, Any]:
    return generate_building(**kwargs)