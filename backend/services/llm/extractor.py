"""
backend/services/llm/extractor.py

Extracts a structured BuildingSchema dict from a natural language prompt
using the local Ollama instance. Falls back to pure rule-based extraction
if Ollama is unavailable or returns unparseable output.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

SYSTEM_PROMPT = """You are an architectural parameter extractor.
Your ONLY job is to read a building description and return a single JSON object.
Do NOT add any explanation, markdown, or code fences — ONLY the raw JSON object.

Required JSON fields:
{
  "building_type": one of ["apartment","villa","office","hotel","warehouse"],
  "floors": integer 1-30,
  "width": float metres,
  "depth": float metres,
  "floor_height": float metres (default 3.2),
  "style": one of ["modern","classical","industrial"],
  "roof_style": one of ["flat","pitched","dome"],
  "balconies": true or false,
  "pool": null OR {"enabled":true,"width":12,"length":6,"depth":1.8},
  "garage": null OR {"enabled":true,"capacity":2}
}

Rules:
- apartment: width ~20, depth ~15, default 5 floors
- villa/house: width ~16, depth ~14, default 2 floors
- office: width ~25, depth ~20, default 8 floors
- Include pool if prompt mentions pool/swimming
- Include garage if prompt mentions garage/parking
- Return ONLY valid JSON, nothing else.
"""


def extract_building_schema_sync(prompt: str) -> dict:
    """Synchronous extraction — safe to call from any context."""
    try:
        raw = _call_ollama(prompt)
        schema = _parse_json(raw)
        if schema:
            return _apply_defaults(schema, prompt)
    except Exception as exc:
        print(f"[Extractor] Ollama failed: {exc}. Using rule-based fallback.")
    return _rule_based(prompt)


def _call_ollama(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 512},
        "prompt": f"{SYSTEM_PROMPT}\n\nUser request: {prompt}\n\nJSON:",
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return data.get("response", "")


def _parse_json(raw: str) -> dict | None:
    # 1. Direct parse
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    # 2. Find first {...} block
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    # 3. Strip markdown fences
    cleaned = re.sub(r'```(?:json)?', '', raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _apply_defaults(schema: dict, prompt: str) -> dict:
    p = prompt.lower()

    if "building_type" not in schema:
        if any(w in p for w in ["villa", "house", "bungalow", "cottage"]):
            schema["building_type"] = "villa"
        elif any(w in p for w in ["office", "commercial", "corporate"]):
            schema["building_type"] = "office"
        else:
            schema["building_type"] = "apartment"

    if "floors" not in schema:
        nums = re.findall(r'\b(\d+)[\s-]*(?:floor|storey|story)', p)
        if nums:
            schema["floors"] = int(nums[0])
        else:
            schema["floors"] = 5 if schema["building_type"] == "apartment" else 2

    if "pool" not in schema:
        schema["pool"] = (
            {"enabled": True, "width": 12, "length": 6, "depth": 1.8}
            if any(w in p for w in ["pool", "swimming", "swim"]) else None
        )

    if "garage" not in schema:
        schema["garage"] = (
            {"enabled": True, "capacity": 2}
            if any(w in p for w in ["garage", "parking", "car park", "carport"]) else None
        )

    schema.setdefault("width", 20.0)
    schema.setdefault("depth", 15.0)
    schema.setdefault("floor_height", 3.2)
    schema.setdefault("style", "modern")
    schema.setdefault("roof_style", "flat")
    schema.setdefault("balconies", True)
    return schema


def _rule_based(prompt: str) -> dict:
    return _apply_defaults({}, prompt)
