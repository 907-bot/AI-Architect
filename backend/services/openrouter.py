"""OpenRouter AI Service"""
import httpx, json, re
from typing import Dict, Any, Optional
import structlog

log = structlog.get_logger()

class OpenRouterService:
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.available = bool(api_key)
        log.info("openrouter_ready" if self.available else "openrouter_missing")

    async def generate(self, prompt: str, w: int = 20, d: int = 30) -> Optional[Dict]:
        if not self.available: return None
        sys_prompt = f"""Return JSON with building_type, style, specs (floors/area), elements (walls/windows/doors with positions), materials, landscape. Plot {w}x{d}m."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as c:
                r = await c.post(f"{self.base_url}/chat/completions", headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, json={"model": "anthropic/claude-3-haiku", "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}], "max_tokens": 2000})
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    m = re.search(r'\{[\s\S]+\}', content)
                    return json.loads(m.group()) if m else None
        except Exception as e: log.error("or_err", error=str(e))
        return None

ai_service = None
def get_ai_service(k: str = ""): global ai_service; ai_service = ai_service or OpenRouterService(k); return ai_service