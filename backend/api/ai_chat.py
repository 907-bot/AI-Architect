"""
backend/api/ai_chat.py
AI Architect Chatbot — OpenAI GPT-4o-mini with tool calling
Handles: architectural questions, image search, building edits, feasibility
"""
from __future__ import annotations
import copy, json, os, re, time, asyncio, urllib.request, urllib.parse
from pathlib import Path
from typing import AsyncIterator, Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI

router = APIRouter()
ROOT   = Path(__file__).resolve().parents[2]
EXPORTS_DIR = ROOT / "exports"

# ── OpenAI client (key from .env) ─────────────────────────────────────────────
def _get_client() -> AsyncOpenAI:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise ValueError("OPENAI_API_KEY not set in .env")
    return AsyncOpenAI(api_key=key)

MODEL = "gpt-4o-mini"   # affordable, fast, tool-calling + vision

# ── Tool definitions ──────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_architectural_images",
            "description": (
                "Search for architectural style images. Use when user asks about "
                "roof types, building styles, materials, or any visual architectural concept. "
                "Returns image URLs to display in chat."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "e.g. 'German Mansard roof architecture'"},
                    "count": {"type": "integer", "default": 4}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_building_element",
            "description": (
                "Modify the current building. Use when user says things like: "
                "'replace the roof', 'change wall color', 'make bedroom larger', "
                "'add a pool', 'change to Japanese style', 'use marble flooring'. "
                "This triggers Blender regeneration."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "element": {
                        "type": "string",
                        "enum": ["roof","walls","style","pool","garage","balconies",
                                 "floor_material","wall_color","furniture_style",
                                 "floors","width","depth","window_style","interior"],
                        "description": "Which element to change"
                    },
                    "value": {
                        "type": "string",
                        "description": "New value, e.g. 'mansard', 'japanese', '#8B4513', 'marble', '6'"
                    },
                    "reason": {"type": "string", "description": "Brief explanation for user"}
                },
                "required": ["element", "value", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_plot_feasibility",
            "description": (
                "Check if a building can be built on a given plot. "
                "Call when user provides plot size or asks if building fits."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plot_area_sqm":  {"type": "number", "description": "Plot area in square metres"},
                    "building_type":  {"type": "string", "default": "apartment"},
                    "floors":         {"type": "integer", "default": 3},
                    "width":          {"type": "number", "default": 20},
                    "depth":          {"type": "number", "default": 15},
                    "country_code":   {"type": "string", "default": "IN"}
                },
                "required": ["plot_area_sqm"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_optimal_building",
            "description": (
                "Autonomously suggest the best building design for a given plot. "
                "Call when user provides plot size + location and wants a recommendation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plot_area_sqm": {"type": "number"},
                    "plot_width_m":  {"type": "number"},
                    "plot_depth_m":  {"type": "number"},
                    "budget_inr":    {"type": "number", "description": "Optional budget in INR"},
                    "preference":    {"type": "string", "description": "User preference e.g. 'family home', 'rental apartment'"},
                    "country_code":  {"type": "string", "default": "IN"}
                },
                "required": ["plot_area_sqm"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_building",
            "description": "Get the current building schema/details. Use when user asks about the current design.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

# ── Image search (DuckDuckGo — no API key needed) ─────────────────────────────
def search_images_ddg(query: str, count: int = 4) -> list[dict]:
    """Free image search via DuckDuckGo. No API key required."""
    try:
        token_url = f"https://duckduckgo.com/?q={urllib.parse.quote(query)}&iax=images&ia=images"
        req = urllib.request.Request(token_url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=8) as r:
            html = r.read().decode("utf-8", errors="ignore")
        vqd = re.search(r'vqd=([\d-]+)', html)
        if not vqd:
            return _fallback_images(query, count)

        img_url = (f"https://duckduckgo.com/i.js?q={urllib.parse.quote(query)}"
                   f"&p=1&vqd={vqd.group(1)}&f=,,,,,&l=wt-wt&o=json&s=0")
        req2 = urllib.request.Request(img_url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://duckduckgo.com/"
        })
        with urllib.request.urlopen(req2, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))

        results = []
        for item in data.get("results", [])[:count]:
            results.append({
                "url":   item.get("image", ""),
                "title": item.get("title", query),
                "thumb": item.get("thumbnail", item.get("image", "")),
                "width": item.get("width", 400),
                "height": item.get("height", 300),
            })
        return results if results else _fallback_images(query, count)
    except Exception as e:
        print(f"[ImageSearch] DDG failed: {e}")
        return _fallback_images(query, count)


def _fallback_images(query: str, count: int) -> list[dict]:
    """Unsplash source as final fallback (free, no key)."""
    keywords = query.replace(" ", ",")
    return [
        {
            "url":   f"https://source.unsplash.com/800x600/?{urllib.parse.quote(keywords)}&sig={i}",
            "title": f"{query} — example {i+1}",
            "thumb": f"https://source.unsplash.com/400x300/?{urllib.parse.quote(keywords)}&sig={i}",
        }
        for i in range(count)
    ]


# ── Tool execution ────────────────────────────────────────────────────────────
async def execute_tool(name: str, args: dict, current_schema: dict) -> dict:
    """Execute a tool call and return the result."""

    if name == "search_architectural_images":
        images = search_images_ddg(args["query"], args.get("count", 4))
        return {
            "type": "images",
            "query": args["query"],
            "images": images,
            "text": f"Here are {len(images)} images of {args['query']}:"
        }

    elif name == "edit_building_element":
        element = args["element"]
        value   = args["value"]
        reason  = args.get("reason", "")

        # Deep-copy so we never mutate the caller's schema dict
        schema = copy.deepcopy(current_schema)

        # ── Special handling for floors: always treat `value` as the DELTA ──────
        if element == "floors":
            word_to_num = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                           "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
            val_lower = str(value).strip().lower()

            # Determine direction (positive/negative)
            sign = 1
            if "-" in val_lower or "remove" in val_lower or "decrease" in val_lower or "reduce" in val_lower or "less" in val_lower or "subtract" in val_lower or "fewer" in val_lower:
                sign = -1

            floors_delta = 1  # default
            digit_match = re.search(r"(\d+)", val_lower)
            if digit_match:
                floors_delta = min(int(digit_match.group(1)), 10)  # cap at 10
            else:
                for word, num in word_to_num.items():
                    if word in val_lower:
                        floors_delta = num
                        break

            actual_delta = sign * floors_delta
            current_floors = schema.get("floors", 1)
            new_floors = max(1, current_floors + actual_delta)
            schema["floors"] = new_floors
            
            action_word = "Added" if actual_delta >= 0 else "Removed"
            abs_delta = abs(actual_delta)
            return {
                "type":      "edit",
                "element":   element,
                "value":     str(schema["floors"]),
                "reason":    f"{action_word} {abs_delta} floor(s)",
                "schema":    schema,
                "regenerate": True,
                "text":      f"✅ {action_word} {abs_delta} floor(s). Building now has {schema['floors']} floors."
            }

        # ── Special handling for width & depth: support relative adjustments ─────
        elif element in ("width", "depth"):
            val_lower = str(value).strip().lower()
            current_val = float(schema.get(element, 20.0 if element == "width" else 15.0))

            multiplier = 1.0
            delta = 0.0

            # 1. Check for percentage change, e.g. "+10%", "10%", "-5%"
            pct_match = re.search(r"([+-]?\d+(?:\.\d+)?)\s*%", val_lower)
            if pct_match:
                pct_val = float(pct_match.group(1))
                multiplier = 1.0 + (pct_val / 100.0)
            else:
                # 2. Check for keywords
                is_increase = any(w in val_lower for w in ("larger", "bigger", "increase", "wider", "deeper", "longer", "add", "grow", "+"))
                is_decrease = any(w in val_lower for w in ("smaller", "reduce", "decrease", "narrower", "shorter", "shrink", "-"))

                # Try to extract a number
                num_match = re.search(r"([+-]?\d+(?:\.\d+)?)", val_lower)
                if num_match:
                    num_val = float(num_match.group(1))
                    if val_lower.startswith("+") or val_lower.startswith("-") or is_increase or is_decrease:
                        sign = -1.0 if (val_lower.startswith("-") or is_decrease) else 1.0
                        delta = sign * abs(num_val)
                    else:
                        if is_increase or is_decrease:
                            sign = -1.0 if is_decrease else 1.0
                            delta = sign * abs(num_val)
                        else:
                            # Plain number, set as absolute value
                            current_val = num_val
                else:
                    # No number, just keywords, e.g. "larger"
                    if is_increase:
                        multiplier = 1.2  # 20% increase
                    elif is_decrease:
                        multiplier = 0.85 # 15% decrease

            new_val = (current_val * multiplier) + delta
            # Enforce limits (5.0m to 100.0m)
            new_val = max(5.0, min(new_val, 100.0))
            new_val = round(new_val, 1)
            schema[element] = new_val

            action_desc = f"Updated {element} to {new_val}m"
            return {
                "type":      "edit",
                "element":   element,
                "value":     str(new_val),
                "reason":    action_desc,
                "schema":    schema,
                "regenerate": True,
                "text":      f"✅ {action_desc} (was {current_val:.1f}m)."
            }

        # ── Map element → schema field (non-floor edits) ─────────────────────────
        FIELD_MAP = {
            "roof":           ("roof_style", value),
            "style":          ("style",      value),
            "walls":          ("wall_color", value),
            "floors":         ("floors",     int(value)),
            "width":          ("width",      float(value)),
            "depth":          ("depth",      float(value)),
            "pool":           ("pool",       {"enabled": value.lower() in ("true","yes","add","on")}),
            "garage":         ("garage",     {"enabled": value.lower() in ("true","yes","add","on")}),
            "balconies":      ("balconies",  value.lower() in ("true","yes","on")),
            "floor_material": ("interior.floor_material", value),
            "wall_color":     ("interior.wall_color",     value),
            "furniture_style":("interior.furniture_style",value),
            "window_style":   ("window_style", value),
            "interior":       ("interior_style", value),
        }
        if element in FIELD_MAP:
            field, val = FIELD_MAP[element]
            if "." in field:
                outer, inner = field.split(".", 1)
                if outer not in schema:
                    schema[outer] = {}
                schema[outer][inner] = val
            else:
                schema[field] = val

        return {
            "type":    "edit",
            "element": element,
            "value":   value,
            "reason":  reason,
            "schema":  schema,
            "regenerate": True,
            "text":    f"✅ {reason or f'Updated {element} to {value}'}"
        }

    elif name == "check_plot_feasibility":
        return _run_feasibility(args, current_schema)

    elif name == "suggest_optimal_building":
        return _suggest_building(args)

    elif name == "get_current_building":
        schema = current_schema or {}
        return {
            "type": "info",
            "text": (
                f"Current building: **{schema.get('floors',3)}-floor "
                f"{schema.get('building_type','apartment')}** "
                f"({schema.get('width',20)}m × {schema.get('depth',15)}m), "
                f"style: **{schema.get('style','modern')}**, "
                f"roof: **{schema.get('roof_style','flat')}**"
                + (f", pool: ✅" if schema.get('pool') else "")
                + (f", garage: ✅" if schema.get('garage') else "")
            )
        }

    return {"type": "text", "text": f"Tool {name} executed."}


def _run_feasibility(args: dict, current_schema: dict) -> dict:
    plot_sqm = args.get("plot_area_sqm", 300)
    btype    = args.get("building_type", current_schema.get("building_type","apartment"))
    floors   = args.get("floors",  current_schema.get("floors", 3))
    bw       = args.get("width",   current_schema.get("width",  20.0))
    bd       = args.get("depth",   current_schema.get("depth",  15.0))
    country  = args.get("country_code", "IN")

    footprint   = bw * bd
    total_area  = footprint * floors
    coverage    = (footprint / plot_sqm) * 100
    far_actual  = total_area / plot_sqm
    setback     = 3.0   # m each side (NBC standard)
    usable_w    = (plot_sqm ** 0.5) - setback * 2  # approx square plot
    usable_d    = usable_w

    # NBC limits
    far_limit = 3.5 if country == "IN" else 2.5
    cov_limit = 50.0

    issues       = []
    suggestions  = []
    feasible     = True

    if coverage > cov_limit:
        feasible = False
        rec_footprint = plot_sqm * cov_limit / 100
        rec_side      = rec_footprint ** 0.5
        issues.append(f"Coverage {coverage:.1f}% exceeds {cov_limit}% limit")
        suggestions.append(f"Reduce building to {rec_side:.1f}m × {rec_side:.1f}m")

    if far_actual > far_limit:
        feasible = False
        max_floors = int((plot_sqm * far_limit) / footprint)
        issues.append(f"FAR {far_actual:.2f} exceeds {far_limit} limit")
        suggestions.append(f"Reduce to {max(1, max_floors)} floors")

    if bw > usable_w or bd > usable_d:
        feasible = False
        issues.append(f"Building {bw}m×{bd}m is too wide for {usable_w:.1f}m×{usable_d:.1f}m usable plot")
        suggestions.append(f"Reduce to {min(bw,usable_w-0.5):.1f}m × {min(bd,usable_d-0.5):.1f}m")

    status = "✅ Feasible" if feasible else "⚠️ Needs adjustment"
    return {
        "type": "feasibility",
        "feasible": feasible,
        "status":   status,
        "metrics": {
            "plot_sqm":     plot_sqm,
            "footprint_sqm": round(footprint, 1),
            "coverage_pct": round(coverage, 1),
            "far_actual":   round(far_actual, 2),
            "far_limit":    far_limit,
            "cov_limit":    cov_limit,
        },
        "issues":      issues,
        "suggestions": suggestions,
        "text": (
            f"{status} — Coverage {coverage:.1f}% (limit {cov_limit}%), "
            f"FAR {far_actual:.2f} (limit {far_limit}). "
            + (" Issues: " + "; ".join(issues) if issues else " All checks passed.")
            + (" Suggestions: " + "; ".join(suggestions) if suggestions else "")
        )
    }


def _suggest_building(args: dict) -> dict:
    plot_sqm = args.get("plot_area_sqm", 300)
    pw       = args.get("plot_width_m",  round(plot_sqm**0.5, 1))
    pd       = args.get("plot_depth_m",  round(plot_sqm**0.5, 1))
    pref     = args.get("preference", "family home")
    budget   = args.get("budget_inr")

    # Calculate optimal building
    setback  = 3.0
    max_w    = max(6, pw - setback*2)
    max_d    = max(6, pd - setback*2)
    footprint = max_w * max_d
    far_limit = 3.5
    max_floor_area = plot_sqm * far_limit
    max_floors = min(15, int(max_floor_area / footprint))

    if "apartment" in pref.lower() or "rental" in pref.lower():
        btype   = "apartment"
        floors  = min(max_floors, 5)
        style   = "modern"
    elif "villa" in pref.lower() or "family" in pref.lower():
        btype   = "villa"
        floors  = min(max_floors, 3)
        style   = "villa"
    else:
        btype   = "apartment"
        floors  = min(max_floors, 4)
        style   = "modern"

    bw  = round(min(max_w, 20), 1)
    bd  = round(min(max_d, 15), 1)
    total_area = bw * bd * floors

    schema = {
        "building_type": btype,
        "floors":  floors,
        "width":   bw,
        "depth":   bd,
        "style":   style,
        "roof_style": "flat" if floors > 2 else "gable",
        "balconies": floors > 1,
    }

    return {
        "type":    "suggestion",
        "schema":  schema,
        "regenerate": True,
        "text": (
            f"🏗️ **Optimal design for your {plot_sqm}m² plot:**\n"
            f"• **{floors}-floor {btype}** — {bw}m × {bd}m\n"
            f"• Total area: {total_area:.0f}m², Coverage: {footprint/plot_sqm*100:.1f}%\n"
            f"• Style: {style.capitalize()}, FAR: {total_area/plot_sqm:.2f}\n"
            f"• This fits within NBC limits. Shall I generate this?"
        )
    }


# ── Request model ─────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message:        str
    history:        list[dict]  = []
    current_schema: dict        = {}
    plot_sqm:       Optional[float] = None
    lat:            Optional[float] = None
    lng:            Optional[float] = None


def _local_edit_tool_calls(message: str) -> list[dict]:
    """Map simple edit commands to local tools so quota/network issues do not block edits."""
    text = (message or "").strip().lower()
    if not text:
        return []

    word_to_num = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "a": 1, "an": 1,
    }

    def amount(default: int = 1) -> int:
        digit = re.search(r"\b(\d+)\b", text)
        if digit:
            return max(1, min(int(digit.group(1)), 10))
        for word, num in word_to_num.items():
            if re.search(rf"\b{re.escape(word)}\b", text):
                return num
        return default

    mentions_floor = any(w in text for w in ("floor", "floors", "storey", "storeys", "story", "stories"))
    if mentions_floor and any(w in text for w in ("add", "increase", "more", "extra", "raise")):
        delta = amount()
        return [{
            "name": "edit_building_element",
            "args": {"element": "floors", "value": str(delta), "reason": f"Added {delta} floor(s)"},
        }]
    if mentions_floor and any(w in text for w in ("remove", "decrease", "reduce", "less", "fewer", "subtract")):
        delta = amount()
        return [{
            "name": "edit_building_element",
            "args": {"element": "floors", "value": f"-{delta}", "reason": f"Removed {delta} floor(s)"},
        }]

    mentions_room_or_size = any(w in text for w in ("room", "rooms", "width", "depth", "larger", "bigger", "wider", "deeper"))
    if mentions_room_or_size and any(w in text for w in ("larger", "bigger", "increase", "wider", "deeper", "expand", "grow")):
        return [
            {
                "name": "edit_building_element",
                "args": {"element": "width", "value": "larger", "reason": "Increased building width"},
            },
            {
                "name": "edit_building_element",
                "args": {"element": "depth", "value": "larger", "reason": "Increased building depth"},
            },
        ]
    if mentions_room_or_size and any(w in text for w in ("smaller", "reduce", "decrease", "narrower", "shorter", "shrink")):
        return [
            {
                "name": "edit_building_element",
                "args": {"element": "width", "value": "smaller", "reason": "Reduced building width"},
            },
            {
                "name": "edit_building_element",
                "args": {"element": "depth", "value": "smaller", "reason": "Reduced building depth"},
            },
        ]

    return []


# ── Streaming chat endpoint ───────────────────────────────────────────────────
@router.post("/ai-chat")
async def ai_chat(body: ChatRequest):
    """POST /api/ai-chat — streaming SSE response with tool calling."""
    return StreamingResponse(
        _stream_chat(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


async def _stream_chat(body: ChatRequest) -> AsyncIterator[str]:
    """Stream chat response as SSE events."""
    def event(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    local_calls = _local_edit_tool_calls(body.message)
    if local_calls:
        accumulated_schema = copy.deepcopy(body.current_schema) if body.current_schema else {}
        for call in local_calls:
            fn_name = call["name"]
            fn_args = call["args"]
            yield event({"type": "tool_start", "tool": fn_name, "args": fn_args})

            result = await execute_tool(fn_name, fn_args, accumulated_schema)
            if result.get("schema"):
                accumulated_schema = result["schema"]

            yield event({"type": "tool_result", "tool": fn_name, "result": result})
            if result.get("regenerate"):
                yield event({
                    "type": "regenerate",
                    "schema": accumulated_schema,
                    "element": fn_args.get("element"),
                    "value": fn_args.get("value"),
                })

        yield event({"type": "done"})
        return

    try:
        client = _get_client()
    except ValueError as e:
        yield event({"type": "error", "text": str(e)})
        return

    # Build system prompt
    schema = body.current_schema or {}
    plot_info = f"Plot: {body.plot_sqm}m²" if body.plot_sqm else "Plot size: not set"
    location  = f"Location: lat={body.lat}, lng={body.lng}" if body.lat else "Location: not set"

    system = f"""You are an expert AI architectural assistant for the AI Architect application.
You help users design, customize, and understand their buildings.

Current building:
- Type: {schema.get('building_type', 'not generated yet')}
- Floors: {schema.get('floors', 'N/A')}
- Dimensions: {schema.get('width', 'N/A')}m × {schema.get('depth', 'N/A')}m
- Style: {schema.get('style', 'N/A')}
- Roof: {schema.get('roof_style', 'N/A')}
- Pool: {'Yes' if schema.get('pool') else 'No'}
- Garage: {'Yes' if schema.get('garage') else 'No'}
{plot_info}
{location}

Your capabilities:
1. Answer architectural questions with relevant images
2. Edit building elements (roof, walls, style, rooms, materials)
3. Check if buildings fit on plots (NBC India / IBC USA compliance)
4. Suggest optimal buildings for given plots autonomously
5. Explain architectural concepts with examples

When user asks about architectural styles or elements, ALWAYS use search_architectural_images.
When user wants to change something, use edit_building_element.

CRITICAL FLOOR & DIMENSION RULES — follow exactly:
- To ADD floors: call edit_building_element(element="floors", value="N") (where N is the positive number of floors to add, e.g. "1", "2")
- To REMOVE floors: call edit_building_element(element="floors", value="-N") (where N is the number of floors to remove, e.g. "-1", "-2")
- NEVER pass the target total floors — always pass only the DELTA (positive to add, negative to remove) as the value.
- To increase room sizes or overall dimensions: call edit_building_element(element="width", value="larger") and/or element="depth", value="larger". Or pass a percentage delta like "+10%" or "+20%".
- To decrease dimensions: call edit_building_element(element="width", value="smaller") and/or element="depth", value="smaller". Or pass a percentage delta like "-10%" or "-15%".
- You can call edit_building_element multiple times in a single response to modify multiple elements simultaneously (e.g. both width and depth to enlarge rooms).

STYLE PRESERVATION: When editing ANY element, only edit that one element. Do NOT change style, roof_style, or any other field unless the user explicitly asked for it.

Be concise, helpful, and proactive. If user gives a plot size, immediately check feasibility."""

    messages = [{"role": "system", "content": system}]
    for h in body.history[-10:]:   # last 10 messages for context
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": body.message})

    # First pass — get tool calls + text (with 429 retry backoff)
    response = None
    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=800,
                temperature=0.7,
            )
            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str and attempt < 2:
                wait = (attempt + 1) * 5  # 5s, 10s
                yield event({"type": "text_chunk", "text": f"⏳ Rate limited — retrying in {wait}s…"})
                await asyncio.sleep(wait)
                # Refresh client in case key was rotated
                try:
                    client = _get_client()
                except ValueError:
                    pass
            else:
                yield event({"type": "error", "text": f"OpenAI error: {e}"})
                return
    if response is None:
        yield event({"type": "error", "text": "OpenAI unavailable after retries. Check your API key quota."})
        return

    msg = response.choices[0].message

    # Stream the text portion first
    if msg.content:
        yield event({"type": "text_chunk", "text": msg.content})

    # Execute tool calls
    accumulated_schema = copy.deepcopy(body.current_schema) if body.current_schema else {}
    if msg.tool_calls:
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            yield event({"type": "tool_start", "tool": fn_name, "args": fn_args})

            result = await execute_tool(fn_name, fn_args, accumulated_schema)
            if result.get("schema"):
                accumulated_schema = result["schema"]

            yield event({"type": "tool_result", "tool": fn_name, "result": result})

            # If this was a building edit → signal frontend to regenerate
            if result.get("regenerate"):
                yield event({
                    "type":   "regenerate",
                    "schema": accumulated_schema,
                    "element": fn_args.get("element"),
                    "value":  fn_args.get("value"),
                })

        # Second pass — natural language summary of tool results
        tool_summaries = []
        for tc in msg.tool_calls:
            try:
                tool_summaries.append({"role":"tool","tool_call_id":tc.id,"content":"Done"})
            except Exception:
                pass

        messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls})
        messages.extend(tool_summaries)

        try:
            follow_up = await client.chat.completions.create(
                model=MODEL, messages=messages, max_tokens=400, temperature=0.7)
            follow_text = follow_up.choices[0].message.content or ""
            if follow_text.strip():
                yield event({"type": "text_chunk", "text": follow_text})
        except Exception:
            pass

    yield event({"type": "done"})


# ── Standalone feasibility endpoint ──────────────────────────────────────────
class FeasibilityRequest(BaseModel):
    plot_area_sqm: float
    plot_width_m:  Optional[float] = None
    plot_depth_m:  Optional[float] = None
    building_type: str   = "apartment"
    floors:        int   = 3
    width:         float = 20.0
    depth:         float = 15.0
    country_code:  str   = "IN"

@router.post("/feasibility")
async def check_feasibility(body: FeasibilityRequest):
    schema = {"building_type": body.building_type,
              "floors": body.floors, "width": body.width, "depth": body.depth}
    return _run_feasibility(body.dict(), schema)

@router.post("/suggest-building")
async def suggest_building(body: FeasibilityRequest):
    return _suggest_building({
        "plot_area_sqm": body.plot_area_sqm,
        "plot_width_m":  body.plot_width_m or body.plot_area_sqm**0.5,
        "plot_depth_m":  body.plot_depth_m or body.plot_area_sqm**0.5,
        "preference":    body.building_type,
    })
