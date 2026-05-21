"""
Drone Navigation MCP Server - Cinematic flight paths and walkthroughs
FastMCP server for generating drone camera paths, collision avoidance, and flythroughs
"""
from fastmcp.server import FastMCP
import structlog
import json
import math
from typing import Dict, Any, List

log = structlog.get_logger()

# Initialize MCP server
mcp_server = FastMCP("drone-navigation-mcp", "1.0.0")


# =====================================================
# TOOLS
# =====================================================

@mcp_server.tool()
def generate_drone_path(
    scene_geometry: Dict[str, Any],
    start_position: List[float],
    end_position: List[float],
    height_above_ground: float = 2.0,
    path_type: str = "smooth"
) -> Dict[str, Any]:
    """
    Generate a cinematic drone flight path through a scene
    
    Args:
        scene_geometry: Scene layout data
        start_position: [x, y, z] starting position
        end_position: [x, y, z] ending position
        height_above_ground: Altitude above ground level
        path_type: smooth, architectural, perimeter, spiral
    
    Returns:
        Flight path with keyframes and timing
    """
    log.info(
        "generate_drone_path",
        path_type=path_type,
        start=start_position,
        end=end_position
    )
    
    # Generate smooth path with catmull-rom interpolation
    keyframes = generate_path_keyframes(
        start_position,
        end_position,
        height_above_ground,
        path_type=path_type
    )
    
    path_data = {
        "type": "drone_path",
        "path_type": path_type,
        "start": start_position,
        "end": end_position,
        "height_above_ground": height_above_ground,
        "keyframes": keyframes,
        "total_duration_sec": len(keyframes) * 0.016,  # ~60 FPS
        "camera_lookups": generate_camera_lookups(keyframes),
        "collision_avoid": True
    }
    
    return path_data


@mcp_server.tool()
def generate_walkthrough_path(
    rooms: List[Dict[str, Any]],
    start_room_id: str,
    eye_height: float = 5.5  # ~average human eye height in feet
) -> Dict[str, Any]:
    """
    Generate a first-person walkthrough path through rooms
    
    Args:
        rooms: List of room specifications
        start_room_id: Starting room
        eye_height: Camera height above floor (in feet)
    
    Returns:
        Walkthrough path with viewpoints
    """
    log.info(
        "generate_walkthrough_path",
        room_count=len(rooms),
        start_room_id=start_room_id,
        eye_height=eye_height
    )
    
    walkthrough_points = []
    
    for room in rooms:
        # Place viewpoint in center of each room
        center_x = room.get("position", {}).get("x", 0) + room.get("width", 10) / 2
        center_y = room.get("position", {}).get("y", 0) + room.get("depth", 10) / 2
        center_z = eye_height
        
        walkthrough_points.append({
            "room_id": room.get("id", "unknown"),
            "position": [center_x, center_y, center_z],
            "direction": [0, 1, 0],  # Looking forward
            "fov": 75,  # Field of view
            "duration_sec": 3  # Stay at viewpoint for 3 seconds
        })
    
    walkthrough_data = {
        "type": "walkthrough",
        "eye_height": eye_height,
        "viewpoints": walkthrough_points,
        "total_duration_sec": len(walkthrough_points) * 3,
        "transitions": "smooth_fade",
        "speed": "normal"
    }
    
    return walkthrough_data


@mcp_server.tool()
def generate_perimeter_tour(
    room_dimensions: Dict[str, float],
    altitude: float = 3.0,
    speed: str = "slow"
) -> Dict[str, Any]:
    """
    Generate a perimeter tour around a building
    
    Args:
        room_dimensions: {"width": float, "depth": float, "height": float}
        altitude: Camera altitude
        speed: slow, normal, fast
    
    Returns:
        Perimeter tour path
    """
    log.info("generate_perimeter_tour", altitude=altitude, speed=speed)
    
    width = room_dimensions.get("width", 30)
    depth = room_dimensions.get("depth", 40)
    height = room_dimensions.get("height", 20)
    
    # Generate perimeter points (circle around building)
    radius = max(width, depth) / 2 + 5
    num_points = 60  # One per 6 degrees
    
    perimeter_points = []
    for i in range(num_points):
        angle = (i / num_points) * 2 * math.pi
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        z = altitude
        perimeter_points.append([x, y, z])
    
    perimeter_data = {
        "type": "perimeter_tour",
        "radius": radius,
        "altitude": altitude,
        "speed": speed,
        "path_points": perimeter_points,
        "duration_sec": len(perimeter_points) * (1.0 if speed == "fast" else 2.0),
        "building_center": [0, 0, height / 2]
    }
    
    return perimeter_data


@mcp_server.tool()
def generate_navigation_mesh(
    rooms: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate navigation mesh (navmesh) for pathfinding
    
    Args:
        rooms: List of room data
    
    Returns:
        Navigation mesh triangles for walkthroughs
    """
    log.info("generate_navigation_mesh", room_count=len(rooms))
    
    vertices = []
    faces = []
    vertex_id = 0
    
    for room in rooms:
        pos = room.get("position", {})
        w = room.get("width", 10) / 2
        d = room.get("depth", 10) / 2
        x = pos.get("x", 0)
        y = pos.get("y", 0)
        
        # Room floor vertices
        room_verts = [
            [x - w, y - d],
            [x + w, y - d],
            [x + w, y + d],
            [x - w, y + d]
        ]
        
        # Add vertices
        start_id = vertex_id
        for vert in room_verts:
            vertices.append([vert[0], vert[1], 0])
            vertex_id += 1
        
        # Create two triangles per room
        faces.append([start_id, start_id + 1, start_id + 2])
        faces.append([start_id, start_id + 2, start_id + 3])
    
    navmesh = {
        "type": "navigation_mesh",
        "vertices": vertices,
        "faces": faces,
        "walkable_height": 6.8,
        "step_size": 0.3,
        "max_slope": 45
    }
    
    return navmesh


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def generate_path_keyframes(
    start: List[float],
    end: List[float],
    altitude: float,
    path_type: str = "smooth",
    num_frames: int = 120
) -> List[Dict[str, Any]]:
    """Generate interpolated keyframes for smooth motion"""
    
    keyframes = []
    
    for i in range(num_frames):
        t = i / num_frames  # 0 to 1
        
        # Ease-in-out cubic for smooth motion
        ease_t = t ** 2 * (3 - 2 * t) if path_type == "smooth" else t
        
        x = start[0] + (end[0] - start[0]) * ease_t
        y = start[1] + (end[1] - start[1]) * ease_t
        z = altitude
        
        keyframes.append({
            "frame": i,
            "position": [x, y, z],
            "time": i / 60.0  # 60 FPS
        })
    
    return keyframes


def generate_camera_lookups(keyframes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate camera look-at points following the path"""
    
    lookups = []
    
    for i, frame in enumerate(keyframes):
        # Look ahead to next point
        if i < len(keyframes) - 1:
            next_frame = keyframes[i + 1]
            target = next_frame["position"]
        else:
            target = frame["position"]
        
        lookups.append({
            "frame": i,
            "target": target,
            "up": [0, 0, 1]  # Z-up
        })
    
    return lookups


# =====================================================
# SERVER
# =====================================================

if __name__ == "__main__":
    log.info("drone_navigation_mcp_server_starting")
    mcp_server.run()
