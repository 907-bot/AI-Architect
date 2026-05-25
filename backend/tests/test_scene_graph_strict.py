"""
Tests for canonical SceneGraph validation and LLM output parsing.
"""
import pytest
import json
from backend.models.scene_graph import SceneGraph, SceneValidator, ArchitecturalStyle


def make_minimal_scene_dict() -> dict:
    return {
        "style": "modern",
        "rooms": [
            {
                "id": "room_1",
                "room_type": "living_room",
                "name": "Living Room",
                "floor_number": 0,
                "position": {"x": 0, "y": 0, "z": 0},
                "width": 5.0,
                "depth": 4.0,
                "height": 3.0,
                "material_id": "mat_1",
                "walls": [],
                "doors": [],
                "windows": [],
                "furniture": [],
                "lights": [],
            }
        ],
        "stairs": [],
        "materials": [
            {"id": "mat_1", "name": "White Paint", "material_type": "paint",
             "color_rgb": "#FFFFFF", "roughness": 0.8, "metallic": 0.0}
        ],
        "lights": [],
        "navigation": {
            "navigation_meshes": [],
            "walkthrough_points": [],
            "drone_path_nodes": [],
        }
    }


def test_scene_graph_valid():
    data = make_minimal_scene_dict()
    sg = SceneGraph(**data)
    sg.compute_properties()
    assert sg.room_count == 1
    assert sg.total_area == 20.0  # 5*4
    assert sg.wall_count == 0
    assert sg.style == ArchitecturalStyle.MODERN


def test_scene_graph_to_dict():
    data = make_minimal_scene_dict()
    sg = SceneGraph(**data)
    d = sg.to_dict()
    assert isinstance(d, dict)
    assert "rooms" in d
    assert len(d["rooms"]) == 1


def test_scene_graph_json_schema():
    schema_str = SceneGraph.schema_json_str()
    schema = json.loads(schema_str)
    assert schema["title"] == "SceneGraph"
    assert "properties" in schema
    assert "rooms" in schema["properties"]


def test_scene_validator_valid():
    data = make_minimal_scene_dict()
    sg = SceneGraph(**data)
    valid, errors = SceneValidator.validate_scene_graph(sg)
    assert valid
    assert len(errors) == 0


def test_scene_validator_invalid_room():
    data = make_minimal_scene_dict()
    data["rooms"][0]["width"] = 1.0  # too small
    sg = SceneGraph(**data)
    valid, errors = SceneValidator.validate_scene_graph(sg)
    assert not valid
    assert any("invalid dimensions" in e for e in errors)


def test_scene_validator_no_walls():
    data = make_minimal_scene_dict()
    sg = SceneGraph(**data)
    valid, errors = SceneValidator.validate_scene_graph(sg)
    assert not valid
    assert any("walls don't form closed loop" in e for e in errors)


def test_llm_output_parse_valid():
    data = make_minimal_scene_dict()
    raw = json.dumps(data)
    success, scene, error = SceneValidator.validate_llm_output(raw)
    assert success
    assert scene is not None
    assert scene.room_count == 1


def test_llm_output_parse_invalid_json():
    raw = "this is not json"
    success, scene, error = SceneValidator.validate_llm_output(raw)
    assert not success
    assert scene is None
    assert "JSON parse failed" in error


def test_llm_output_parse_missing_field():
    data = make_minimal_scene_dict()
    del data["rooms"]
    raw = json.dumps(data)
    success, scene, error = SceneValidator.validate_llm_output(raw)
    assert not success
    assert scene is None
    assert "validation failed" in error


def test_duplicate_room_ids():
    data = make_minimal_scene_dict()
    # Add second room with same id
    data["rooms"].append(data["rooms"][0].copy())
    with pytest.raises(ValueError, match="Duplicate room IDs"):
        SceneGraph(**data)
