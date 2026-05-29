from backend.scene_graph import compile_scene
from backend.toon.editor import edit_toon
from backend.toon.parser import parse_toon
from backend.toon.planner import prompt_to_toon
from backend.toon.prompt_meta import infer_features


def test_toon_parser_supports_house_room_roof_style():
    toon = """
    HOUSE modern_villa {
      STYLE modern
      ROOM living_room {
        size 8x6
      }
      ROOM bedroom {
        size 5x5
      }
      ROOF flat
    }
    """

    scene = parse_toon(toon)

    assert scene.house.name == "modern_villa"
    assert scene.house.style == "modern"
    assert scene.house.roof.kind == "flat"
    assert [room.name for room in scene.house.rooms] == ["living_room", "bedroom"]


def test_prompt_to_scene_graph_to_viewer_geometry():
    toon = prompt_to_toon("Modern 3 bedroom villa with flat roof")
    scene = parse_toon(toon)
    geometry = compile_scene(scene)

    assert len(scene.house.rooms) >= 8
    assert geometry["meshes"]
    assert geometry["floor_plan"]["rooms"]
    assert geometry["floor_plan"]["doors"]
    assert geometry["floor_plan"]["windows"]
    assert any(mesh["component_group"] == "Roof" for mesh in geometry["meshes"])


def test_five_storey_apartment_prompt():
    prompt = "build a 5 storey apartment with swimming pool and garage"
    toon = prompt_to_toon(prompt)
    scene = parse_toon(toon)
    scene.house.features = infer_features(prompt)
    assert scene.house.num_floors == 5
    assert "pool" in scene.house.features or any("garage" in r.name for r in scene.house.rooms)
    geo = compile_scene(scene)
    assert geo["total_height_m"] >= 15
    assert any(m["id"] == "pool" for m in geo["meshes"])
    assert any(m["component_group"] == "Roof" and m["type"] == "box" for m in geo["meshes"])


def test_prompt_generates_multi_floor_toon():
    toon = prompt_to_toon("Modern 2 story 3 bedroom villa with balcony and garage")
    assert "FLOORS 2" in toon
    assert "FLOOR 0" in toon
    assert "FLOOR 1" in toon

    scene = parse_toon(toon)
    assert scene.house.num_floors == 2
    assert any(room.floor > 0 for room in scene.house.rooms)
    assert any(room.room_type == "bedroom" and room.floor > 0 for room in scene.house.rooms)


def test_parser_respects_floor_directives():
    toon = """
    HOUSE duplex {
      STYLE modern
      FLOORS 2
      FLOOR 0
      ROOM living_room { type living_room size 8x6 }
      FLOOR 1
      ROOM bedroom { type bedroom size 5x5 }
      ROOF flat
    }
  """
    scene = parse_toon(toon)
    living = next(room for room in scene.house.rooms if room.name == "living_room")
    bedroom = next(room for room in scene.house.rooms if room.name == "bedroom")
    assert living.floor == 0
    assert bedroom.floor == 1


def test_edit_toon_makes_named_room_larger():
    toon = prompt_to_toon("Modern 1 bedroom villa")
    edited, scene, changed = edit_toon(toon, "Make living room larger")

    living = next(room for room in scene.house.rooms if room.name == "living_room")
    assert "living_room" in changed
    assert living.width > 8
    assert "size" in edited
