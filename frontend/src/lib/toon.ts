/**
 * TOON — Token-Oriented Object Notation (TypeScript).
 * Compact token-replacement encoding for fast WebSocket communication.
 *
 * Token dictionary MUST stay in sync with backend/utils/toon.py.
 *
 * Usage:
 *   import { toonEncode, toonDecode } from "@/lib/toon";
 *   const encoded = toonEncode({ rooms: [{ id: "r1", width: 5.0 }] });
 *   const decoded = toonDecode(encoded);
 *   // encoded → '{2:[{3:"r1",6:5.0}]}'
 */

// =====================================================
// TOKEN REGISTRY — MUST stay in sync with backend
// =====================================================

const TOKENS: Record<number, string> = {
  // Generic (1-19)
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

  // Envelope & Response (20-29)
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

  // Scene Graph core (30-74)
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

  // Navigation (75-84)
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

  // Events (85-99)
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

  // Scene metadata (100-109)
  100: "generation_prompt",
  101: "generation_parameters",
  102: "asset_urls",
  103: "room_tags",
  104: "total_area",
  105: "room_count",
  106: "wall_count",

  // Compliance (110-132)
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

  // Generation parameters (133-145)
  133: "budget",
  134: "occupancy",
  135: "include_garage",
  136: "include_basement",
  137: "target_sqft",
  138: "num_bedrooms",
  139: "num_bathrooms",
  140: "flooring_type",
  142: "plot_lat",
  143: "plot_lng",

  // API response extras (150-159)
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

  // Identity & auth (160-165)
  160: "username",
  161: "email",
  162: "password",
  163: "token",
  164: "access_token",
  165: "token_type",

  // Artifact (170-174)
  170: "stage",
  174: "artifact_id",
  175: "progress_label",

  // Scene graph stored in DB (180-189)
  180: "scene_graph",
  183: "room_tags",
  184: "glb",
  185: "splat",
  186: "thumbnail",
  187: "preview_frames",
  188: "meshes",
  189: "mesh_type",
};

// Build reverse map
const REVERSE_TOKENS: Record<string, number> = {};
for (const [k, v] of Object.entries(TOKENS)) {
  REVERSE_TOKENS[v] = Number(k);
}

// =====================================================
// TOON ENCODER
// =====================================================

function encodeValue(val: unknown): string {
  if (val === null || val === undefined) return "null";
  if (typeof val === "boolean") return val ? "true" : "false";
  if (typeof val === "number") return Number.isFinite(val) ? String(val) : "null";
  if (typeof val === "string") {
    const escaped = val
      .replace(/\\/g, "\\\\")
      .replace(/"/g, '\\"')
      .replace(/\n/g, "\\n");
    return `"${escaped}"`;
  }
  if (Array.isArray(val)) return encodeList(val);
  if (typeof val === "object") return encodeDict(val as Record<string, unknown>);
  return `"${String(val)}"`;
}

function encodeList(lst: unknown[]): string {
  const items = lst.map(encodeValue);
  return "[" + items.join(",") + "]";
}

function encodeDict(d: Record<string, unknown>): string {
  const pairs: string[] = [];
  for (const [k, v] of Object.entries(d)) {
    const token = REVERSE_TOKENS[k];
    const encodedKey = token !== undefined ? String(token) : encodeValue(k);
    const encodedVal = encodeValue(v);
    pairs.push(`${encodedKey}:${encodedVal}`);
  }
  return "{" + pairs.join(",") + "}";
}

export function toonEncode(obj: unknown): string {
  return encodeValue(obj);
}

// =====================================================
// TOON DECODER
// =====================================================

class ToonParseError extends Error {
  constructor(msg: string) {
    super(msg);
    this.name = "ToonParseError";
  }
}

class ToonParser {
  private src: string;
  private pos: number = 0;

  constructor(source: string) {
    this.src = source;
  }

  private peek(): string | undefined {
    return this.pos < this.src.length ? this.src[this.pos] : undefined;
  }

  private advance(): string {
    return this.src[this.pos++];
  }

  private skipWs(): void {
    while (this.pos < this.src.length && " \t\n\r".includes(this.src[this.pos])) {
      this.pos++;
    }
  }

  parse(): unknown {
    this.skipWs();
    const ch = this.peek();
    if (ch === "{") return this.parseDict();
    if (ch === "[") return this.parseList();
    if (ch === '"') return this.parseString();
    if (ch === "-" || (ch !== undefined && ch >= "0" && ch <= "9")) return this.parseNumber();
    if (ch === "n") return this.parseLiteral("null", null);
    if (ch === "t") return this.parseLiteral("true", true);
    if (ch === "f") return this.parseLiteral("false", false);
    throw new ToonParseError(`Unexpected character '${ch}' at pos ${this.pos}`);
  }

  private parseLiteral(expected: string, value: unknown): unknown {
    if (this.src.slice(this.pos, this.pos + expected.length) === expected) {
      this.pos += expected.length;
      return value;
    }
    throw new ToonParseError(`Expected '${expected}' at pos ${this.pos}`);
  }

  private parseString(): string {
    if (this.advance() !== '"') throw new ToonParseError("Expected opening quote");
    const chars: string[] = [];
    while (this.pos < this.src.length) {
      const ch = this.advance();
      if (ch === '"') return chars.join("");
      if (ch === "\\") {
        if (this.pos < this.src.length) {
          const nxt = this.advance();
          if (nxt === "n") chars.push("\n");
          else if (nxt === '"') chars.push('"');
          else if (nxt === "\\") chars.push("\\");
          else chars.push(nxt);
        } else {
          chars.push(ch);
        }
      } else {
        chars.push(ch);
      }
    }
    throw new ToonParseError("Unterminated string");
  }

  private parseNumber(): number {
    const start = this.pos;
    if (this.peek() === "-") this.advance();
    while (this.pos < this.src.length && "0123456789".includes(this.src[this.pos])) {
      this.advance();
    }
    let isFloat = false;
    if (this.pos < this.src.length && this.src[this.pos] === ".") {
      isFloat = true;
      this.advance();
      while (this.pos < this.src.length && "0123456789".includes(this.src[this.pos])) {
        this.advance();
      }
    }
    const raw = this.src.slice(start, this.pos);
    return isFloat ? parseFloat(raw) : parseInt(raw, 10);
  }

  private parseList(): unknown[] {
    if (this.advance() !== "[") throw new ToonParseError("Expected '['");
    const items: unknown[] = [];
    this.skipWs();
    if (this.peek() === "]") {
      this.advance();
      return items;
    }
    while (true) {
      this.skipWs();
      items.push(this.parse());
      this.skipWs();
      const ch = this.advance();
      if (ch === "]") return items;
      if (ch !== ",") throw new ToonParseError(`Expected ',' or ']' in list, got '${ch}'`);
    }
  }

  private parseDict(): Record<string, unknown> {
    if (this.advance() !== "{") throw new ToonParseError("Expected '{'");
    const obj: Record<string, unknown> = {};
    this.skipWs();
    if (this.peek() === "}") {
      this.advance();
      return obj;
    }
    while (true) {
      this.skipWs();
      const key = this.parse();
      this.skipWs();
      if (this.advance() !== ":") throw new ToonParseError("Expected ':' after key");
      this.skipWs();
      const val = this.parse();
      this.skipWs();
      // Resolve integer token back to string key
      if (typeof key === "number") {
        const resolved = TOKENS[key];
        obj[resolved ?? String(key)] = val as Record<string, unknown>;
      } else {
        obj[String(key)] = val as Record<string, unknown>;
      }
      this.skipWs();
      const ch = this.advance();
      if (ch === "}") return obj;
      if (ch !== ",") throw new ToonParseError(`Expected ',' or '}}' in dict, got '${ch}'`);
    }
  }
}

export function toonDecode(source: string): unknown {
  if (!source || !source.trim()) throw new ToonParseError("Empty input");
  const parser = new ToonParser(source.trim());
  const result = parser.parse();
  parser.skipWs();
  if (parser.pos < parser.src.length) {
    const remaining = parser.src.slice(parser.pos).trim();
    if (remaining) throw new ToonParseError(`Trailing data: '${remaining.slice(0, 50)}...'`);
  }
  return result;
}

// =====================================================
// CONVENIENCE WRAPPER
// =====================================================

/**
 * Decode a TOON message from WebSocket.
 * If the message is JSON (backward compat), parse as JSON.
 */
export function decodeMessage(raw: string): unknown {
  if (!raw || !raw.trim()) return null;
  const trimmed = raw.trim();
  if (trimmed.startsWith('{"') || trimmed.startsWith("[")) {
    try {
      return JSON.parse(trimmed);
    } catch {
      return toonDecode(trimmed);
    }
  }
  return toonDecode(trimmed);
}
