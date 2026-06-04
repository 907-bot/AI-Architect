"""
backend/tests/test_semantic_edits.py
Tests for the semantic editing logic in editor.py (edit_toon).
No OpenAI / LLM calls — all logic is purely rule-based.
"""
import pytest
from backend.toon.planner import prompt_to_toon
from backend.toon.editor import edit_toon
from backend.toon.parser import parse_toon


# ── Shared fixture ────────────────────────────────────────────────────────────

SAMPLE_TOON = """
HOUSE sample_house {
  STYLE modern
  FLOORS 3
  ROOM living_room {
    size 8x6
    height 3
  }
  ROOM bedroom {
    size 5x5
    height 3
  }
  ROOM kitchen {
    size 4x4
    height 3
  }
  ROOF flat
}
"""


def _base_scene():
    """Parse the sample toon into a SceneGraph."""
    return parse_toon(SAMPLE_TOON)


# ── Floor Addition ────────────────────────────────────────────────────────────

class TestFloorAddition:
    def test_add_a_floor_increments_by_1(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "add a floor")
        assert scene.house.num_floors == 4
        assert any("floor" in c.lower() for c in changed)

    def test_add_one_more_floor(self):
        """Matches the '+1 Floor' chip prompt."""
        _, scene, changed = edit_toon(SAMPLE_TOON, "Add one more floor")
        assert scene.house.num_floors == 4
        assert any("floor" in c.lower() for c in changed)

    def test_add_2_floors(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "add 2 floors")
        assert scene.house.num_floors == 5
        assert any("floor" in c.lower() for c in changed)

    def test_add_two_floors_word(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "add two more floors")
        assert scene.house.num_floors == 5
        assert any("floor" in c.lower() for c in changed)

    def test_extra_floor(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "add an extra floor")
        assert scene.house.num_floors == 4
        assert any("floor" in c.lower() for c in changed)


# ── Floor Removal ─────────────────────────────────────────────────────────────

class TestFloorRemoval:
    def test_remove_a_floor_decrements_by_1(self):
        """Core bug fix: 'remove a floor' must decrement, not add or no-op."""
        _, scene, changed = edit_toon(SAMPLE_TOON, "remove a floor")
        assert scene.house.num_floors == 2
        assert any("floor" in c.lower() for c in changed)

    def test_remove_one_floor(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "Remove one floor")
        assert scene.house.num_floors == 2
        assert any("floor" in c.lower() for c in changed)

    def test_decrease_floors(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "decrease floors by 1")
        assert scene.house.num_floors == 2
        assert any("floor" in c.lower() for c in changed)

    def test_fewer_floors(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "make it have fewer floors")
        assert scene.house.num_floors == 2
        assert any("floor" in c.lower() for c in changed)

    def test_reduce_floors(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "reduce the number of floors")
        assert scene.house.num_floors == 2
        assert any("floor" in c.lower() for c in changed)

    def test_remove_2_floors(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "remove 2 floors")
        assert scene.house.num_floors == 1
        assert any("floor" in c.lower() for c in changed)

    def test_remove_floor_minimum_clamped_to_1(self):
        """Even if user asks to remove 10 floors from a 1-floor house, stays at 1."""
        single_floor_toon = SAMPLE_TOON.replace("FLOORS 3", "FLOORS 1")
        _, scene, changed = edit_toon(single_floor_toon, "remove a floor")
        assert scene.house.num_floors == 1  # clamped at minimum

    def test_remove_does_not_increase(self):
        """Bug guard: 'remove a floor' must never increase floor count."""
        _, scene, _ = edit_toon(SAMPLE_TOON, "remove a floor")
        assert scene.house.num_floors < 3


# ── Room Resizing ─────────────────────────────────────────────────────────────

class TestRoomResizing:
    def test_make_rooms_larger_enlarges_all_rooms(self):
        """Core bug fix: 'make the rooms larger' applies to ALL rooms, not zero."""
        _, scene, changed = edit_toon(SAMPLE_TOON, "make the rooms larger")
        assert len(changed) > 0, "Expected at least one room to be changed"
        for room in scene.house.rooms:
            orig = _base_scene().house.rooms
            orig_room = next((r for r in orig if r.name == room.name), None)
            if orig_room:
                assert room.width >= orig_room.width, f"{room.name} width should not shrink"
                assert room.depth >= orig_room.depth, f"{room.name} depth should not shrink"

    def test_make_all_rooms_larger(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "make all rooms larger")
        assert len(changed) == len(scene.house.rooms)

    def test_wider_rooms_enlarges_rooms(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "wider rooms")
        assert len(changed) > 0

    def test_rooms_larger_scale_factor_is_1_2(self):
        """Width and depth must be scaled by 1.2x."""
        base = _base_scene()
        _, scene, _ = edit_toon(SAMPLE_TOON, "make the rooms larger")
        for room in scene.house.rooms:
            base_room = next((r for r in base.house.rooms if r.name == room.name), None)
            if base_room:
                assert abs(room.width - round(base_room.width * 1.2, 2)) < 0.01
                assert abs(room.depth - round(base_room.depth * 1.2, 2)) < 0.01

    def test_make_specific_room_larger(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "Make living room larger")
        living = next(r for r in scene.house.rooms if r.name == "living_room")
        assert "living_room" in changed or "living room" in " ".join(changed)
        assert living.width > 8

    def test_make_rooms_smaller(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "make the rooms smaller")
        assert len(changed) > 0
        for room in scene.house.rooms:
            base_room = next((r for r in _base_scene().house.rooms if r.name == room.name), None)
            if base_room:
                assert room.width <= base_room.width


# ── Roof Edits ────────────────────────────────────────────────────────────────

class TestRoofEdits:
    def test_change_to_gable_roof(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "change roof to gable")
        assert scene.house.roof.kind == "gable"
        assert "roof" in changed

    def test_change_to_hip_roof(self):
        _, scene, changed = edit_toon(SAMPLE_TOON, "hip roof please")
        assert scene.house.roof.kind == "hip"


# ── No-op safety ──────────────────────────────────────────────────────────────

class TestNoOpSafety:
    def test_unrelated_instruction_changes_nothing(self):
        """Non-edit instructions must not corrupt the scene."""
        _, scene, changed = edit_toon(SAMPLE_TOON, "what is the building height")
        assert changed == []
        assert scene.house.num_floors == 3

    def test_add_floor_then_remove_floor_is_net_zero(self):
        """Adding and removing a floor should restore the original count."""
        toon_after_add, _, _ = edit_toon(SAMPLE_TOON, "add a floor")
        _, scene_final, _ = edit_toon(toon_after_add, "remove a floor")
        assert scene_final.house.num_floors == 3
