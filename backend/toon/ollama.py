from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from backend.toon.parser import parse_toon
from backend.toon.planner import prompt_to_toon


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")  # Using Llama 3.1 as specified


def check_ollama_connection() -> tuple[bool, str | None, str | None]:
    """Check if Ollama is running and accessible"""
    try:
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/tags",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models]
                # Check for llama3.1 or similar
                has_llama = any("llama" in m.lower() for m in model_names)
                return True, model_names[0] if model_names else OLLAMA_MODEL, None
    except Exception as e:
        return False, None, str(e)
    return False, None, "Ollama not responding"


SYSTEM_PROMPT = """You generate TOON scripts for an architectural compiler.
Return valid TOON only. No markdown. No prose.

Supported grammar:
HOUSE name {
  STYLE modern
  ROOM living_room {
    type living_room
    size 8x6
  }
  ROOM hallway {
    type hallway
    size 2x5
  }
  ROOM bedroom_1 {
    type bedroom
    size 5x5
  }
  ROOM kitchen {
    type kitchen
    size 4x4
  }
  ROOF flat
}

Rules:
- Include living_room, hallway, kitchen, at least one bathroom, and requested bedrooms.
- Use meters.
- Keep rooms realistic: bedrooms about 4x4 to 6x5, living about 7x5 to 10x7.
- Do not generate Blender code.
"""


def prompt_to_toon_with_ollama(prompt: str, model: str | None = None) -> tuple[str, str]:
    requested_model = model or OLLAMA_MODEL
    try:
        toon = _call_ollama(prompt, requested_model)
        parse_toon(toon)
        return toon, f"ollama:{requested_model}"
    except Exception:
        fallback = prompt_to_toon(prompt)
        return fallback, "deterministic-fallback"


def _call_ollama(prompt: str, model: str) -> str:
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0.15},
        "prompt": f"{SYSTEM_PROMPT}\n\nUser request: {prompt}\n\nTOON:",
    }
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError("Ollama is not reachable") from exc
    return _extract_toon(data.get("response", ""))


def _extract_toon(text: str) -> str:
    stripped = text.strip()
    if "```" in stripped:
        chunks = [chunk.strip() for chunk in stripped.split("```") if "HOUSE" in chunk]
        if chunks:
            stripped = chunks[0]
            if stripped.lower().startswith("toon"):
                stripped = stripped[4:].strip()
    start = stripped.find("HOUSE")
    if start < 0:
        raise ValueError("Ollama response did not contain TOON HOUSE block")
    return stripped[start:].strip()
