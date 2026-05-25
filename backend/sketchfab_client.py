"""
Sketchfab Integration — MCP Server + Direct API Client
Handles: search, download, cache, and metadata extraction
"""
import httpx
import structlog
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio

log = structlog.get_logger()

# ====================================================
# CONFIG
# ====================================================

SKETCHFAB_API_URL = "https://api.sketchfab.com/v3"
SKETCHFAB_DOWNLOAD_URL = "https://api.sketchfab.com/v3/models/{uid}/download"
CACHE_DIR = Path("./cache/sketchfab")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class SketchfabConfig:
    """Configuration loaded from environment"""
    def __init__(self):
        self.api_token = os.environ.get("SKETCHFAB_API_TOKEN", "")
        self.mcp_server_url = os.environ.get("SKETCHFAB_MCP_URL", "")
        self.enable_mcp = bool(self.mcp_server_url)
        self.max_results = 24
        self.download_format = "glb"  # glb, gltf, usdz

config = SketchfabConfig()

# ====================================================
# DIRECT SKETCHFAB API CLIENT
# ====================================================

class SketchfabClient:
    """
    Direct REST client for Sketchfab API.
    Falls back to this if MCP server is unavailable.
    """

    def __init__(self, api_token: str = None):
        self.api_token = api_token or config.api_token
        self.client = httpx.AsyncClient(
            base_url=SKETCHFAB_API_URL,
            headers={"Authorization": f"Token {self.api_token}"} if self.api_token else {},
            timeout=30.0,
            follow_redirects=True
        )

    async def search(
        self,
        query: str,
        category: str = None,      # "furniture", "architecture", "decor", "exterior"
        max_results: int = 24,
        animated: bool = False,
        downloadable: bool = True,
        sort_by: str = "relevance"   # relevance, recent, likes, views
    ) -> List[Dict[str, Any]]:
        """
        Search Sketchfab for 3D models.
        Returns list of model metadata.
        """
        params = {
            "type": "models",
            "q": query,
            "count": min(max_results, 100),
            "sort_by": sort_by,
            "animated": str(animated).lower(),
            "downloadable": str(downloadable).lower(),
        }
        if category:
            params["categories"] = category

        try:
            resp = await self.client.get("/search", params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            log.info("sketchfab_search", query=query, count=len(results))
            return [self._normalize_model(m) for m in results]
        except Exception as e:
            log.error("sketchfab_search_error", query=query, error=str(e))
            return []

    async def get_model_details(self, uid: str) -> Optional[Dict[str, Any]]:
        """Fetch full model metadata including download URLs"""
        try:
            resp = await self.client.get(f"/models/{uid}")
            resp.raise_for_status()
            return self._normalize_model(resp.json())
        except Exception as e:
            log.error("sketchfab_model_error", uid=uid, error=str(e))
            return None

    async def get_download_url(self, uid: str) -> Optional[str]:
        """
        Get temporary download URL for a model.
        Requires the model to be downloadable and API token.
        """
        if not self.api_token:
            log.warning("sketchfab_no_token", uid=uid)
            return None

        try:
            resp = await self.client.get(f"/models/{uid}/download")
            resp.raise_for_status()
            data = resp.json()
            # Sketchfab returns gldf (gltf) or glb options
            glb = data.get("glb", {})
            url = glb.get("url")
            log.info("sketchfab_download_url", uid=uid, has_url=bool(url))
            return url
        except Exception as e:
            log.error("sketchfab_download_error", uid=uid, error=str(e))
            return None

    async def download_model(self, uid: str, filename: str = None) -> Optional[Path]:
        """
        Download model GLB to local cache.
        Returns path to cached file.
        """
        cache_file = CACHE_DIR / f"{uid}.glb"
        if cache_file.exists():
            log.info("sketchfab_cache_hit", uid=uid)
            return cache_file

        url = await self.get_download_url(uid)
        if not url:
            return None

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=60) as dl:
                resp = await dl.get(url)
                resp.raise_for_status()
                cache_file.write_bytes(resp.content)
                log.info("sketchfab_downloaded", uid=uid, size=len(resp.content))
                return cache_file
        except Exception as e:
            log.error("sketchfab_download_failed", uid=uid, error=str(e))
            return None

    def _normalize_model(self, raw: Dict) -> Dict[str, Any]:
        """Normalize Sketchfab API response to our schema"""
        return {
            "uid": raw.get("uid"),
            "name": raw.get("name", "Untitled"),
            "description": raw.get("description", ""),
            "thumbnail": raw.get("thumbnails", {}).get("images", [{}])[0].get("url", ""),
            "author": raw.get("user", {}).get("displayName", "Unknown"),
            "vertex_count": raw.get("vertexCount"),
            "face_count": raw.get("faceCount"),
            "is_downloadable": raw.get("isDownloadable", False),
            "is_restricted": raw.get("isRestricted", False),
            "license": raw.get("license", {}).get("label", "Unknown"),
            "categories": [c.get("name") for c in raw.get("categories", [])],
            "tags": raw.get("tags", []),
            "view_count": raw.get("viewCount", 0),
            "like_count": raw.get("likeCount", 0),
            "price": raw.get("price"),
            "embed_url": raw.get("embedUrl"),
        }

    async def close(self):
        await self.client.aclose()


# ====================================================
# MCP SERVER WRAPPER
# ====================================================

class SketchfabMCPClient:
    """
    Client for Sketchfab MCP Server (if deployed separately).
    Communicates via HTTP/JSON-RPC or stdio depending on deployment.
    """

    def __init__(self, mcp_url: str = None):
        self.mcp_url = mcp_url or config.mcp_server_url
        self.client = httpx.AsyncClient(base_url=self.mcp_url, timeout=60) if self.mcp_url else None

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search via MCP server"""
        if not self.client:
            return []
        try:
            resp = await self.client.post("/search", json={"query": query, **kwargs})
            resp.raise_for_status()
            return resp.json().get("results", [])
        except Exception as e:
            log.error("mcp_search_error", error=str(e))
            return []

    async def place_asset(self, uid: str, position: Dict[str, float], room: str = None) -> Dict[str, Any]:
        """Ask MCP to place an asset in a room context"""
        if not self.client:
            return {"error": "MCP not configured"}
        try:
            resp = await self.client.post("/place", json={
                "uid": uid,
                "position": position,
                "room": room
            })
            return resp.json()
        except Exception as e:
            return {"error": str(e)}


# ====================================================
# UNIFIED FACADE
# ====================================================

class SketchfabManager:
    """
    Unified interface: tries MCP first, falls back to direct API.
    """

    def __init__(self):
        self.direct = SketchfabClient()
        self.mcp = SketchfabMCPClient()
        self.use_mcp = config.enable_mcp and self.mcp.client is not None

    async def search(
        self,
        query: str,
        category: str = None,
        context: str = None,   # "interior", "exterior", "landscape"
        max_results: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Smart search with context awareness.
        If context is provided, enhances query (e.g., "interior" + "sofa" → "sofa furniture interior")
        """
        enhanced_query = query
        if context:
            enhanced_query = f"{query} {context}"

        if self.use_mcp:
            results = await self.mcp.search(enhanced_query, category=category, max_results=max_results)
            if results:
                return results

        return await self.direct.search(enhanced_query, category=category, max_results=max_results)

    async def get_asset(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get asset metadata + download URL + cached file path"""
        meta = await self.direct.get_model_details(uid)
        if not meta:
            return None

        cache_path = await self.direct.download_model(uid)
        meta["local_path"] = str(cache_path) if cache_path else None
        meta["download_url"] = await self.direct.get_download_url(uid)
        return meta

    async def get_or_download(self, uid: str) -> Optional[Path]:
        """Get cached file path, downloading if necessary"""
        return await self.direct.download_model(uid)

    async def close(self):
        await self.direct.close()


# Global instance
_sketchfab_manager: Optional[SketchfabManager] = None

def get_sketchfab_manager() -> SketchfabManager:
    global _sketchfab_manager
    if _sketchfab_manager is None:
        _sketchfab_manager = SketchfabManager()
    return _sketchfab_manager
