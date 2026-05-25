"""
TOON — Token-Oriented Object Notation.
Compact token-replacement encoding for fast WebSocket and API communication.

Tokens replace string keys with small integers, reducing payload size 40-70%.
Token dictionary is shared between backend (Python) and frontend (TypeScript).

Usage:
    encoded = toon_encode({"rooms": [{"id": "r1", "width": 5.0}]})
    decoded = toon_decode(encoded)
    # encoded → '{2:[{3:"r1",6:5.0}]}'
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import structlog

log = structlog.get_logger()


# =====================================================
# TOKEN REGISTRY — Single source of truth
# Extend this whenever adding new keys to the system.
# Frontend TypeScript version MUST stay in sync.
# =====================================================

TOKENS: Dict[int, str] = {
    # Generic (1-19)
    1: "type",
    2: "id",
    3: "name",
    4: "timestamp",
    5: "status",
    6: "message",
    7: "data",
    8: "error",
    9: "detail",
    10: "version",
    11: "metadata",
    12: "success",
    13: "path",
    14: "status_code",
    15: "scene_id",
    16: "session_id",
    17: "client_id",
    18: "user_id",
    19: "project_id",

    # Envelope & Response (20-29)
    20: "scene",
    21: "agent_executions",
    22: "execution_id",
    23: "token_usage",
    24: "model_used",
    25: "execution_time_ms",
    26: "created_at",
    27: "updated_at",
    28: "completed_at",
    29: "description",

    # Scene Graph core (30-69)
    30: "rooms",
    31: "stairs",
    32: "materials",
    33: "lights",
    34: "navigation",
    35: "walls",
    36: "doors",
    37: "windows",
    38: "furniture",
    39: "style",
    40: "room_type",
    41: "floor_number",
    42: "position",
    43: "width",
    44: "depth",
    45: "height",
    46: "rotation",
    47: "material_id",
    48: "scale",
    49: "color_rgb",
    50: "roughness",
    51: "metallic",
    52: "texture_url",
    53: "albedo_url",
    54: "normal_url",
    55: "material_type",
    56: "model_id",
    57: "room_id",
    58: "window_type",
    59: "door_type",
    60: "connects_to_room",
    61: "furniture_type",
    62: "light_type",
    63: "intensity",
    64: "range",
    65: "angle",
    66: "pitch",
    67: "yaw",
    68: "roll",
    69: "start_point",
    70: "end_point",
    71: "thickness",
    72: "x",
    73: "y",
    74: "z",

    # Navigation (75-84)
    75: "navigation_meshes",
    76: "walkthrough_points",
    77: "drone_path_nodes",
    78: "vertices",
    79: "faces",
    80: "drone_path",
    81: "look_at",
    82: "duration_s",
    83: "index",
    84: "component_group",

    # Event fields (85-99)
    85: "agent",
    86: "phase",
    87: "progress_pct",
    88: "change_type",
    89: "changes",
    90: "valid",
    91: "errors",
    92: "artifact_url",
    93: "artifact_type",
    94: "preview_url",
    95: "event",
    96: "payload",
    97: "subscription_id",
    98: "active_connections",
    99: "sessions",

    # Scene metadata (100-109)
    100: "generation_prompt",
    101: "generation_parameters",
    102: "asset_urls",
    103: "room_tags",
    104: "total_area",
    105: "room_count",
    106: "wall_count",

    # Compliance (110-129)
    110: "compliant",
    111: "issues",
    112: "actual_far",
    113: "allowed_far",
    114: "actual_coverage_pct",
    115: "allowed_coverage_pct",
    116: "vastu_suggestions",
    117: "seismic_zone",
    118: "severity",
    119: "actual",
    120: "allowed",
    121: "reference",
    122: "zone",
    123: "occupancy",
    124: "plot_width",
    125: "plot_depth",
    126: "building_width",
    127: "building_depth",
    128: "building_height",
    129: "num_floors",
    130: "set_front",
    131: "set_rear",
    132: "set_side",

    # Generation parameters (133-149)
    133: "budget",
    134: "occupancy",
    135: "include_garage",
    136: "include_basement",
    137: "target_sqft",
    138: "num_bedrooms",
    139: "num_bathrooms",
    140: "flooring_type",
    141: "num_floors",
    142: "plot_lat",
    143: "plot_lng",
    144: "plot_width",
    145: "plot_depth",

    # API response extras (150-159)
    150: "app_name",
    151: "app_version",
    152: "database",
    153: "features",
    154: "api_docs",
    155: "documentation",
    156: "health",
    157: "offset",
    158: "limit",
    159: "total",

    # Identity & auth (160-169)
    160: "username",
    161: "email",
    162: "password",
    163: "token",
    164: "access_token",
    165: "token_type",

    # Artifact (170-179)
    170: "stage",
    171: "artifact_url",
    172: "artifact_type",
    173: "preview_url",
    174: "artifact_id",
    175: "progress_label",

    # Metadata keys often used in JSON graph
    180: "scene_graph",
    181: "generation_prompt",
    182: "asset_urls",
    183: "room_tags",
    184: "glb",
    185: "splat",
    186: "thumbnail",
    187: "preview_frames",
    188: "meshes",
    189: "mesh_type",
}

# Build reverse map: str → int
REVERSE_TOKENS: Dict[str, int] = {v: k for k, v in TOKENS.items()}


# =====================================================
# TOON ENCODER
# =====================================================

def _encode_value(val: Any) -> str:
    """Encode a Python value to TOON token notation."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        escaped = val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    if isinstance(val, dict):
        return _encode_dict(val)
    if isinstance(val, (list, tuple)):
        return _encode_list(val)
    return f'"{str(val)}"'


def _encode_list(lst: Union[List, Tuple]) -> str:
    items = [_encode_value(v) for v in lst]
    return "[" + ",".join(items) + "]"


def _encode_dict(d: Dict) -> str:
    pairs = []
    for k, v in d.items():
        if isinstance(k, str):
            token = REVERSE_TOKENS.get(k)
            if token is not None:
                encoded_key = str(token)
            else:
                # Unknown key — keep as string
                encoded_key = _encode_value(k)
        elif isinstance(k, int):
            encoded_key = str(k)
        else:
            encoded_key = _encode_value(k)
        encoded_val = _encode_value(v)
        pairs.append(f"{encoded_key}:{encoded_val}")
    return "{" + ",".join(pairs) + "}"


def toon_encode(obj: Any) -> str:
    """Encode a Python object to TOON string."""
    return _encode_value(obj)


# =====================================================
# TOON DECODER
# =====================================================

class ToonParseError(Exception):
    pass


class _ToonParser:
    """Recursive descent parser for TOON format."""

    def __init__(self, source: str):
        self.src = source
        self.pos = 0

    def peek(self) -> Optional[str]:
        if self.pos < len(self.src):
            return self.src[self.pos]
        return None

    def advance(self) -> str:
        ch = self.src[self.pos]
        self.pos += 1
        return ch

    def skip_ws(self):
        while self.pos < len(self.src) and self.src[self.pos] in " \t\n\r":
            self.pos += 1

    def parse(self) -> Any:
        self.skip_ws()
        ch = self.peek()
        if ch == "{":
            return self._parse_dict()
        if ch == "[":
            return self._parse_list()
        if ch == '"':
            return self._parse_string()
        if ch in "-0123456789":
            return self._parse_number()
        if ch == "n":
            return self._parse_literal("null", None)
        if ch == "t":
            return self._parse_literal("true", True)
        if ch == "f":
            return self._parse_literal("false", False)
        raise ToonParseError(f"Unexpected character '{ch}' at pos {self.pos}")

    def _parse_literal(self, expected: str, value: Any) -> Any:
        if self.src[self.pos:self.pos + len(expected)] == expected:
            self.pos += len(expected)
            return value
        raise ToonParseError(f"Expected '{expected}' at pos {self.pos}")

    def _parse_string(self) -> str:
        if self.advance() != '"':
            raise ToonParseError("Expected opening quote")
        chars = []
        while self.pos < len(self.src):
            ch = self.advance()
            if ch == '"':
                return "".join(chars)
            if ch == "\\":
                if self.pos < len(self.src):
                    nxt = self.advance()
                    if nxt == "n":
                        chars.append("\n")
                    elif nxt == '"':
                        chars.append('"')
                    elif nxt == "\\":
                        chars.append("\\")
                    else:
                        chars.append(nxt)
                else:
                    chars.append(ch)
            else:
                chars.append(ch)
        raise ToonParseError("Unterminated string")

    def _parse_number(self) -> Union[int, float]:
        start = self.pos
        if self.peek() == "-":
            self.advance()
        while self.pos < len(self.src) and self.src[self.pos] in "0123456789":
            self.advance()
        is_float = False
        if self.pos < len(self.src) and self.src[self.pos] == ".":
            is_float = True
            self.advance()
            while self.pos < len(self.src) and self.src[self.pos] in "0123456789":
                self.advance()
        raw = self.src[start:self.pos]
        return float(raw) if is_float else int(raw)

    def _parse_list(self) -> List:
        if self.advance() != "[":
            raise ToonParseError("Expected '['")
        items = []
        self.skip_ws()
        if self.peek() == "]":
            self.advance()
            return items
        while True:
            self.skip_ws()
            items.append(self.parse())
            self.skip_ws()
            ch = self.advance()
            if ch == "]":
                return items
            if ch != ",":
                raise ToonParseError(f"Expected ',' or ']' in list, got '{ch}'")

    def _parse_dict(self) -> Dict:
        if self.advance() != "{":
            raise ToonParseError("Expected '{'")
        obj = {}
        self.skip_ws()
        if self.peek() == "}":
            self.advance()
            return obj
        while True:
            self.skip_ws()
            # Parse key (integer token or string)
            key = self.parse()
            self.skip_ws()
            if self.advance() != ":":
                raise ToonParseError("Expected ':' after key in dict")
            self.skip_ws()
            val = self.parse()
            self.skip_ws()
            # Convert integer tokens back to string keys
            if isinstance(key, int):
                resolved = TOKENS.get(key)
                if resolved is not None:
                    obj[resolved] = val
                else:
                    obj[str(key)] = val
            else:
                obj[key] = val
            self.skip_ws()
            ch = self.advance()
            if ch == "}":
                return obj
            if ch != ",":
                raise ToonParseError(f"Expected ',' or '}}' in dict, got '{ch}'")


def toon_decode(source: str) -> Any:
    """Decode a TOON string back to a Python object."""
    if not isinstance(source, str) or not source.strip():
        raise ToonParseError("Empty input")
    parser = _ToonParser(source.strip())
    result = parser.parse()
    # Ensure full input consumed
    parser.skip_ws()
    if parser.pos < len(parser.src):
        remaining = parser.src[parser.pos:].strip()
        if remaining:
            raise ToonParseError(f"Trailing data after end: '{remaining[:50]}...'")
    return result


# =====================================================
# CONTENT TYPE HELPERS
# =====================================================

TOON_CONTENT_TYPE = "application/x-toon"


def toon_dumps(obj: Any) -> str:
    """Alias for toon_encode: serialize to TOON string."""
    return toon_encode(obj)


def toon_loads(source: str) -> Any:
    """Alias for toon_decode: deserialize from TOON string."""
    return toon_decode(source)
