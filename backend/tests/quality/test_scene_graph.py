from backend.models.scene_graph import (
    SceneGraph,
    RoomSpec,
    Vector3,
    RoomType,
    SceneValidator,
)


def make_valid_room(room_id: str) -> RoomSpec:
    return RoomSpec(
        id=room_id,
        room_type=RoomType.BEDROOM,
        name="Bedroom",
        floor_number=1,
        position=Vector3(x=0, y=0, z=0),
        width=12,
        depth=12,
        height=9,
        material_id="mat_1",
        walls=[],
        windows=[],
        doors=[],
        furniture=[],
        lights=[],
    )


def test_scene_graph_compute_properties():
    room = make_valid_room("r1")
    scene = SceneGraph(
        rooms=[room],
        stairs=[],
        materials=[],
        lights=[],
        navigation={"navigation_meshes": [], "walkthrough_points": [], "drone_path_nodes": []},
    )

    scene.compute_properties()
    assert scene.room_count == 1
    assert scene.total_area == 12 * 12
    assert scene.room_count == len(scene.rooms)


def test_scene_validator_positive():
    room = make_valid_room("r2")
    scene = SceneGraph(
        rooms=[room],
        stairs=[],
        materials=[],
        lights=[],
        navigation={"navigation_meshes": [], "walkthrough_points": [], "drone_path_nodes": []},
    )
    ok, errors = SceneValidator.validate_scene_graph(scene)
    assert ok
    assert errors == []


def test_scene_validator_negative_dimensions():
    room = make_valid_room("r3")
    room.width = 1.0   # below 2m minimum → invalid
    room.depth = 1.0
    room.height = 5
    scene = SceneGraph(
        rooms=[room],
        stairs=[],
        materials=[],
        lights=[],
        navigation={"navigation_meshes": [], "walkthrough_points": [], "drone_path_nodes": []},
    )
    ok, errors = SceneValidator.validate_scene_graph(scene)
    assert not ok
    assert len(errors) > 0
