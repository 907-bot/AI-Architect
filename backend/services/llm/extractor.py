"""
backend/services/llm/extractor.py
Extracts structured BuildingSchema from natural language. Detects all styles.
"""
from __future__ import annotations
import json, os, re, urllib.request

OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

SYSTEM_PROMPT = """You are an architectural parameter extractor.
Return ONLY a single valid JSON object — no markdown, no explanation.

Required fields:
{
  "building_type": "apartment"|"villa"|"office"|"hotel"|"warehouse",
  "floors": integer 1-30,
  "width": float metres,
  "depth": float metres,
  "floor_height": float (default 3.2),
  "style": "modern"|"japanese"|"villa"|"asian"|"industrial"|"scandinavian"|"colonial"|"classical",
  "roof_style": "flat"|"pitched"|"hip"|"pagoda"|"curved"|"shed"|"gable"|"steep_gable",
  "balconies": true|false,
  "pool": null OR {"enabled":true,"width":12,"length":6,"depth":1.8},
  "garage": null OR {"enabled":true,"capacity":2}
}

Style mapping rules:
- "japanese","japan","zen","wabi","kyoto","tokyo" → style="japanese", roof_style="pagoda"
- "asian","chinese","oriental","beijing","shanghai" → style="asian", roof_style="curved"
- "villa","mediterranean","tuscany","spanish","colonial" → style="villa", roof_style="hip"
- "scandinavian","nordic","norwegian","swedish","danish","hygge" → style="scandinavian", roof_style="steep_gable"
- "industrial","warehouse","loft","factory","brick" → style="industrial", roof_style="shed"
- "colonial","georgian","american","federal" → style="colonial", roof_style="gable"
- "classical","greek","roman","neoclassical","baroque" → style="classical", roof_style="pitched"
- default → style="modern", roof_style="flat"

Size rules:
- apartment: width=20, depth=15, default 5 floors
- villa/house: width=16, depth=14, default 2 floors
- office: width=25, depth=20, default 8 floors
- japanese villa: width=14, depth=12, default 2 floors

Return ONLY valid JSON."""

STYLE_KEYWORDS = {
    "japanese": ["japanese","japan","zen","wabi","kyoto","tokyo","sakura","shoji","tatami","pagoda"],
    "asian":    ["asian","chinese","oriental","beijing","shanghai","china","feng shui","dynasty"],
    "villa":    ["villa","mediterranean","tuscany","spanish","tuscan","terracotta","courtyard"],
    "scandinavian":["scandinavian","nordic","norwegian","swedish","danish","hygge","fjord"],
    "industrial":  ["industrial","warehouse","loft","factory","exposed brick","steampunk","brutalist"],
    "colonial": ["colonial","georgian","american","federal","craftsman","farmhouse"],
    "classical":["classical","greek","roman","neoclassical","baroque","renaissance","parthenon"],
    "modern":   ["modern","contemporary","minimalist","glass","steel","futuristic","sleek"],
}

ROOF_FOR_STYLE = {
    "japanese":"pagoda","asian":"curved","villa":"hip","scandinavian":"steep_gable",
    "industrial":"shed","colonial":"gable","classical":"pitched","modern":"flat",
}

def extract_building_schema_sync(prompt: str) -> dict:
    try:
        raw    = _call_ollama(prompt)
        schema = _parse_json(raw)
        if schema:
            return _apply_defaults(schema, prompt)
    except Exception as exc:
        print(f"[Extractor] Ollama failed: {exc}. Using rule-based fallback.")
    return _rule_based(prompt)

def _call_ollama(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL, "stream": False,
        "options": {"temperature": 0.05, "num_predict": 600},
        "prompt": f"{SYSTEM_PROMPT}\n\nUser request: {prompt}\n\nJSON:",
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=35) as r:
        return json.loads(r.read().decode()).get("response", "")

def _parse_json(raw: str) -> dict | None:
    for attempt in [raw.strip(), re.sub(r'```(?:json)?','',raw).strip()]:
        try: return json.loads(attempt)
        except: pass
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        try: return json.loads(m.group())
        except: pass
    return None

def _detect_style(prompt: str) -> str:
    p = prompt.lower()
    for style, keywords in STYLE_KEYWORDS.items():
        if any(k in p for k in keywords):
            return style
    return "modern"

def _apply_defaults(schema: dict, prompt: str) -> dict:
    p = prompt.lower()

    if "building_type" not in schema:
        if any(w in p for w in ["villa","house","bungalow","cottage","home"]):
            schema["building_type"] = "villa"
        elif any(w in p for w in ["office","commercial","corporate","business"]):
            schema["building_type"] = "office"
        else:
            schema["building_type"] = "apartment"

    if "floors" not in schema:
        nums = re.findall(r'\b(\d+)[\s-]*(?:floor|storey|story|level)', p)
        if nums:
            schema["floors"] = int(nums[0])
        else:
            defaults = {"villa":2,"office":8,"hotel":6,"warehouse":1}
            schema["floors"] = defaults.get(schema["building_type"], 5)

    # Style detection — trust LLM if provided, otherwise detect from prompt
    if "style" not in schema or schema["style"] not in STYLE_KEYWORDS:
        schema["style"] = _detect_style(prompt)

    # Auto-set matching roof_style
    if "roof_style" not in schema:
        schema["roof_style"] = ROOF_FOR_STYLE.get(schema["style"], "flat")

    if "pool" not in schema:
        schema["pool"] = (
            {"enabled":True,"width":12,"length":6,"depth":1.8}
            if any(w in p for w in ["pool","swimming","swim"]) else None)

    if "garage" not in schema:
        schema["garage"] = (
            {"enabled":True,"capacity":2}
            if any(w in p for w in ["garage","parking","car park","carport"]) else None)

    schema.setdefault("width",      20.0 if schema["building_type"]!="villa" else 16.0)
    schema.setdefault("depth",      15.0 if schema["building_type"]!="villa" else 14.0)
    schema.setdefault("floor_height", 3.2)
    schema.setdefault("balconies",  True)
    return schema

def _rule_based(prompt: str) -> dict:
    return _apply_defaults({}, prompt)
