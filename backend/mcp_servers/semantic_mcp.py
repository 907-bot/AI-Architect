"""
Semantic Scene MCP Server - Language-aware scene understanding
FastMCP server for CLIP-based semantic search and scene querying
"""
from fastmcp.server import FastMCP
import structlog
import json
from typing import Dict, Any, List

log = structlog.get_logger()

# Initialize MCP server
mcp_server = FastMCP("semantic-scene-mcp", "1.0.0")


# =====================================================
# TOOLS
# =====================================================

@mcp_server.tool()
def semantic_search(
    scene_data: Dict[str, Any],
    query: str
) -> Dict[str, Any]:
    """
    Semantic search within a scene using natural language
    
    Args:
        scene_data: Complete scene graph
        query: Natural language query (e.g., "find red furniture in bedrooms")
    
    Returns:
        List of matching scene objects with confidence scores
    """
    log.info("semantic_search", query=query)
    
    # STUBBED: In production, would use CLIP embeddings + cosine similarity
    # For MVP, use keyword matching
    
    results = []
    
    # Extract keywords from query
    keywords = extract_keywords(query)
    
    # Search scene objects
    scene_objects = extract_scene_objects(scene_data)
    
    for obj in scene_objects:
        score = calculate_semantic_match(obj, keywords)
        if score > 0.3:  # Threshold
            results.append({
                "object_id": obj.get("id"),
                "object_type": obj.get("type"),
                "position": obj.get("position"),
                "confidence": score,
                "match_reason": generate_match_reason(obj, keywords)
            })
    
    # Sort by confidence
    results.sort(key=lambda x: x["confidence"], reverse=True)
    
    return {
        "type": "semantic_search_results",
        "query": query,
        "results": results[:10],  # Top 10
        "total_matches": len(results)
    }


@mcp_server.tool()
def tag_scene_objects(
    scene_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Automatically tag all scene objects with semantic labels
    
    Args:
        scene_data: Complete scene graph
    
    Returns:
        Scene with semantic tags on all objects
    """
    log.info("tag_scene_objects")
    
    # STUBBED: In production, would use vision models
    
    tagged_scene = scene_data.copy()
    
    # Tag rooms
    if "rooms" in tagged_scene:
        for room in tagged_scene["rooms"]:
            room["semantic_tags"] = get_room_tags(room)
    
    # Tag furniture
    if "furniture" in tagged_scene:
        for item in tagged_scene["furniture"]:
            item["semantic_tags"] = get_furniture_tags(item)
    
    # Tag materials
    if "materials" in tagged_scene:
        for material in tagged_scene["materials"]:
            material["semantic_tags"] = get_material_tags(material)
    
    return {
        "type": "tagged_scene",
        "tagged_objects": count_tagged_objects(tagged_scene)
    }


@mcp_server.tool()
def find_rooms_by_feature(
    scene_data: Dict[str, Any],
    feature: str
) -> Dict[str, Any]:
    """
    Find all rooms with a specific feature
    
    Args:
        scene_data: Scene graph
        feature: Feature name (e.g., "large_windows", "fireplace", "hardwood_floor")
    
    Returns:
        List of rooms matching the feature
    """
    log.info("find_rooms_by_feature", feature=feature)
    
    matching_rooms = []
    
    rooms = scene_data.get("rooms", [])
    for room in rooms:
        tags = room.get("semantic_tags", [])
        if feature.lower() in [t.lower() for t in tags]:
            matching_rooms.append({
                "room_id": room.get("id"),
                "room_type": room.get("type"),
                "position": room.get("position"),
                "dimensions": {
                    "width": room.get("width"),
                    "depth": room.get("depth"),
                    "height": room.get("height")
                }
            })
    
    return {
        "type": "rooms_by_feature",
        "feature": feature,
        "matching_rooms": matching_rooms,
        "count": len(matching_rooms)
    }


@mcp_server.tool()
def describe_scene(
    scene_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a natural language description of the scene
    
    Args:
        scene_data: Scene graph
    
    Returns:
        Detailed description and statistics
    """
    log.info("describe_scene")
    
    rooms = scene_data.get("rooms", [])
    furniture = scene_data.get("furniture", [])
    materials = scene_data.get("materials", [])
    
    # Count room types
    room_types = {}
    for room in rooms:
        rt = room.get("type", "unknown")
        room_types[rt] = room_types.get(rt, 0) + 1
    
    # Calculate statistics
    total_area = sum(r.get("width", 0) * r.get("depth", 0) for r in rooms)
    avg_room_height = sum(r.get("height", 0) for r in rooms) / len(rooms) if rooms else 0
    
    # Generate description
    description = f"This is a {len(rooms)}-room residential architecture. "
    
    if room_types:
        descriptions = []
        for rt, count in room_types.items():
            descriptions.append(f"{count} {rt}(s)")
        description += f"It contains {', '.join(descriptions)}. "
    
    description += f"Total floor area is approximately {int(total_area)} square feet. "
    description += f"Average ceiling height is {avg_room_height:.1f} feet. "
    
    return {
        "type": "scene_description",
        "description": description,
        "statistics": {
            "room_count": len(rooms),
            "room_types": room_types,
            "total_area_sqft": int(total_area),
            "avg_ceiling_height_ft": round(avg_room_height, 1),
            "furniture_count": len(furniture),
            "material_count": len(materials)
        }
    }


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def extract_keywords(query: str) -> List[str]:
    """Extract keywords from natural language query"""
    # Simple tokenization
    words = query.lower().split()
    # Remove common stop words
    stop_words = {"the", "a", "an", "in", "on", "at", "to", "for", "and", "or", "is"}
    return [w for w in words if w not in stop_words and len(w) > 2]


def extract_scene_objects(scene_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten scene hierarchy into searchable objects"""
    objects = []
    
    for room in scene_data.get("rooms", []):
        room_copy = room.copy()
        room_copy["type"] = "room"
        objects.append(room_copy)
    
    for item in scene_data.get("furniture", []):
        item_copy = item.copy()
        item_copy["type"] = "furniture"
        objects.append(item_copy)
    
    for material in scene_data.get("materials", []):
        mat_copy = material.copy()
        mat_copy["type"] = "material"
        objects.append(mat_copy)
    
    return objects


def calculate_semantic_match(obj: Dict[str, Any], keywords: List[str]) -> float:
    """Calculate semantic similarity score"""
    score = 0.0
    
    # Check object attributes
    obj_text = str(obj).lower()
    
    for keyword in keywords:
        if keyword in obj_text:
            score += 0.5 / len(keywords)
    
    return min(score, 1.0)


def generate_match_reason(obj: Dict[str, Any], keywords: List[str]) -> str:
    """Generate human-readable match reason"""
    obj_type = obj.get("type", "object")
    obj_name = obj.get("name", obj.get("id", ""))
    return f"Matched {obj_type} '{obj_name}' containing keywords"


def get_room_tags(room: Dict[str, Any]) -> List[str]:
    """Generate semantic tags for a room"""
    tags = []
    
    room_type = room.get("type", "").lower()
    tags.append(room_type)
    
    # Size-based tags
    area = room.get("width", 0) * room.get("depth", 0)
    if area > 300:
        tags.append("spacious")
    elif area < 100:
        tags.append("compact")
    else:
        tags.append("medium_sized")
    
    # Height-based tags
    height = room.get("height", 0)
    if height > 12:
        tags.append("high_ceiling")
    
    return tags


def get_furniture_tags(furniture: Dict[str, Any]) -> List[str]:
    """Generate semantic tags for furniture"""
    ftype = furniture.get("type", "").lower()
    return [ftype, furniture.get("category", "").lower()]


def get_material_tags(material: Dict[str, Any]) -> List[str]:
    """Generate semantic tags for materials"""
    mtype = material.get("type", "").lower()
    color = material.get("color", "").lower()
    return [mtype, color] if color else [mtype]


def count_tagged_objects(scene: Dict[str, Any]) -> int:
    """Count total tagged objects"""
    count = 0
    count += len(scene.get("rooms", []))
    count += len(scene.get("furniture", []))
    count += len(scene.get("materials", []))
    return count


# =====================================================
# SERVER
# =====================================================

if __name__ == "__main__":
    log.info("semantic_scene_mcp_server_starting")
    mcp_server.run()
