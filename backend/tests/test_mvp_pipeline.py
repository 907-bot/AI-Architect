from backend.scene_graph import compile_scene
from backend.toon.editor import edit_toon
from backend.toon.parser import parse_toon
from backend.toon.planner import prompt_to_toon


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

    assert len(scene.house.rooms) == 4
    assert geometry["meshes"]
    assert any(mesh["component_group"] == "Roof" for mesh in geometry["meshes"])


def test_edit_toon_makes_named_room_larger():
    toon = prompt_to_toon("Modern 1 bedroom villa")
    edited, scene, changed = edit_toon(toon, "Make living room larger")

    living = next(room for room in scene.house.rooms if room.name == "living_room")
    assert "living_room" in changed
    assert living.width > 8
    assert "size" in edited
