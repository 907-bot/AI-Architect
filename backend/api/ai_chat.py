"""
backend/api/ai_chat.py
AI Architect Chatbot — OpenAI GPT-4o-mini with tool calling
Handles: architectural questions, image search, building edits, feasibility
"""
from __future__ import annotations
import json, os, re, time, asyncio, urllib.request, urllib.parse
from pathlib import Path
from typing import AsyncIterator
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
        # Map element → schema field
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
        }
        if element in FIELD_MAP:
            field, val = FIELD_MAP[element]
            if "." in field:
                outer, inner = field.split(".", 1)
                if outer not in current_schema:
                    current_schema[outer] = {}
                current_schema[outer][inner] = val
            else:
                current_schema[field] = val

        return {
            "type":    "edit",
            "element": element,
            "value":   value,
            "reason":  args.get("reason", ""),
            "schema":  current_schema,
            "regenerate": True,
            "text":    f"✅ {args.get('reason', f'Updated {element} to {value}')}"
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
    plot_sqm:       float | None = None
    lat:            float | None = None
    lng:            float | None = None


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
Be concise, helpful, and proactive. If user gives a plot size, immediately check feasibility."""

    messages = [{"role": "system", "content": system}]
    for h in body.history[-10:]:   # last 10 messages for context
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": body.message})

    # First pass — get tool calls + text
    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=800,
            temperature=0.7,
        )
    except Exception as e:
        yield event({"type": "error", "text": f"OpenAI error: {e}"})
        return

    msg = response.choices[0].message

    # Stream the text portion first
    if msg.content:
        yield event({"type": "text_chunk", "text": msg.content})

    # Execute tool calls
    if msg.tool_calls:
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            yield event({"type": "tool_start", "tool": fn_name, "args": fn_args})

            result = await execute_tool(fn_name, fn_args, dict(body.current_schema))

            yield event({"type": "tool_result", "tool": fn_name, "result": result})

            # If this was a building edit → signal frontend to regenerate
            if result.get("regenerate"):
                yield event({
                    "type":   "regenerate",
                    "schema": result.get("schema", body.current_schema),
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
    plot_width_m:  float | None = None
    plot_depth_m:  float | None = None
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
