"""
Sketchfab Integration — Direct API Client
Handles: search, download (ZIP extraction), cache, and metadata normalization

Based on Sketchfab Data API v3:
  https://docs.sketchfab.com/data-api/v3/index.html
  https://sketchfab.com/developers/data-api/v3/python

Key API facts:
  - Base URL:   https://api.sketchfab.com/v3
  - Auth:       Authorization: Token {api_token}
  - Download:   GET /models/{uid}/download → returns {"gltf": {"url": "...", "size": N}, ...}
                The URL is a temporary S3 link to a ZIP archive (not a raw GLB).
                Must download ZIP and extract the .gltf / .glb inside.
  - Search:     GET /search?type=models&q=...&downloadable=true&count=N&sort_by=-likeCount
  - Tags:       Returned as [{"name": "sofa", "slug": "sofa"}, ...] — extract .name
  - Categories: Slugs like "furniture-home", "nature-plants" (not free text)
  - sort_by:    Use "-relevance", "-likeCount", "-viewCount", "-publishedAt" (minus = desc)
"""
import httpx
import structlog
import os
import json
import zipfile
import io
from typing import List, Dict, Any, Optional
from pathlib import Path

log = structlog.get_logger()

# ====================================================
# CONFIG
# ====================================================

SKETCHFAB_API_URL = "https://api.sketchfab.com/v3"
CACHE_DIR = Path("./cache/sketchfab")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Official Sketchfab category slugs for the categories= search param
CATEGORY_SLUGS = {
    "furniture": "furniture-home",
    "architecture": "architecture",
    "nature": "nature-plants",
    "decor": "furniture-home",
    "exterior": "architecture",
    "vehicle": "cars-vehicles",
    "animals": "animals-pets",
    "food": "food-drink",
}


class SketchfabConfig:
    """Configuration loaded from environment"""
    def __init__(self):
        self.api_token = os.environ.get("SKETCHFAB_API_TOKEN", "")
        self.mcp_server_url = os.environ.get("SKETCHFAB_MCP_URL", "")
        self.enable_mcp = bool(self.mcp_server_url)
        self.max_results = 24


config = SketchfabConfig()


# ====================================================
# DIRECT SKETCHFAB API CLIENT
# ====================================================

class SketchfabClient:
    """
    Direct REST client for Sketchfab Data API v3.

    Auth: Authorization: Token {api_token}
    Ref:  https://sketchfab.com/developers/data-api/v3
    """

    def __init__(self, api_token: str = None):
        self.api_token = api_token or config.api_token
        self.headers = (
            {"Authorization": f"Token {self.api_token}"}
            if self.api_token else {}
        )
        self.client = httpx.AsyncClient(
            base_url=SKETCHFAB_API_URL,
            headers=self.headers,
            timeout=30.0,
            follow_redirects=True,
        )

    async def search(
        self,
        query: str,
        category: str = None,
        max_results: int = 24,
        downloadable: bool = True,
        sort_by: str = "-likeCount",   # API uses minus prefix for descending
    ) -> List[Dict[str, Any]]:
        """
        Search Sketchfab for 3D models.

        Official params:
          type=models, q=..., count=N, downloadable=true/false,
          sort_by=-relevance|-likeCount|-viewCount|-publishedAt,
          categories=furniture-home (optional slug)
        """
        params: Dict[str, Any] = {
            "type": "models",
            "q": query,
            "count": min(max_results, 100),
            "sort_by": sort_by,
            "downloadable": "true" if downloadable else "false",
        }

        # Map our friendly category names to official Sketchfab slugs
        if category:
            slug = CATEGORY_SLUGS.get(category.lower(), category)
            params["categories"] = slug

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
        """Fetch full model metadata. GET /models/{uid}"""
        try:
            resp = await self.client.get(f"/models/{uid}")
            resp.raise_for_status()
            return self._normalize_model(resp.json())
        except Exception as e:
            log.error("sketchfab_model_error", uid=uid, error=str(e))
            return None

    async def get_download_url(self, uid: str) -> Optional[str]:
        """
        Get temporary S3 download URL for a model ZIP archive.

        Official response format:
          GET /models/{uid}/download
          → {"gltf": {"url": "https://s3.../archive.zip", "size": 12345}, ...}

        NOTE: The URL points to a ZIP file, not a raw GLB.
        Use download_model() to automatically extract it.
        Requires API token + model must be downloadable.
        """
        if not self.api_token:
            log.warning("sketchfab_no_token", uid=uid)
            return None

        try:
            resp = await self.client.get(f"/models/{uid}/download")
            resp.raise_for_status()
            data = resp.json()

            # Official API returns "gltf" key (ZIP archive), not "glb"
            # Try gltf first (most common), fallback to source
            for fmt in ("gltf", "glb", "source"):
                entry = data.get(fmt, {})
                url = entry.get("url")
                if url:
                    log.info("sketchfab_download_url", uid=uid, format=fmt, has_url=True)
                    return url

            log.warning("sketchfab_no_download_url", uid=uid, keys=list(data.keys()))
            return None
        except Exception as e:
            log.error("sketchfab_download_error", uid=uid, error=str(e))
            return None

    async def download_model(self, uid: str) -> Optional[Path]:
        """
        Download model to local cache and extract GLB from ZIP.

        Sketchfab delivers downloads as a ZIP archive containing:
          - scene.gltf / scene.glb
          - textures/
          - etc.

        Returns path to the extracted .glb file (or .gltf if no glb found).
        """
        cache_glb = CACHE_DIR / f"{uid}.glb"
        if cache_glb.exists():
            log.info("sketchfab_cache_hit", uid=uid)
            return cache_glb

        url = await self.get_download_url(uid)
        if not url:
            return None

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=120) as dl:
                resp = await dl.get(url)
                resp.raise_for_status()
                content = resp.content
                log.info("sketchfab_download_raw", uid=uid, size=len(content))

            # Sketchfab delivers a ZIP archive — extract the GLB/GLTF
            extracted = self._extract_glb_from_zip(content, uid)
            if extracted:
                log.info("sketchfab_extracted", uid=uid, path=str(extracted))
                return extracted

            # Fallback: if content is already a binary GLB (magic bytes glTF)
            if content[:4] == b"glTF":
                cache_glb.write_bytes(content)
                log.info("sketchfab_raw_glb_saved", uid=uid)
                return cache_glb

            log.warning("sketchfab_unknown_format", uid=uid)
            return None

        except Exception as e:
            log.error("sketchfab_download_failed", uid=uid, error=str(e))
            return None

    def _extract_glb_from_zip(self, zip_bytes: bytes, uid: str) -> Optional[Path]:
        """
        Extract GLB/GLTF from the downloaded ZIP archive.
        Saves all extracted files under cache/{uid}/ and returns the main GLB path.
        """
        try:
            model_dir = CACHE_DIR / uid
            model_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                zf.extractall(model_dir)

                # Find the primary .glb or .gltf file
                names = zf.namelist()
                glb_files = [n for n in names if n.lower().endswith(".glb")]
                gltf_files = [n for n in names if n.lower().endswith(".gltf")]

                target = None
                if glb_files:
                    target = model_dir / glb_files[0]
                elif gltf_files:
                    target = model_dir / gltf_files[0]

                if target and target.exists():
                    # Copy to the flat cache path for easy serving
                    dest = CACHE_DIR / f"{uid}.glb"
                    dest.write_bytes(target.read_bytes())
                    return dest

        except zipfile.BadZipFile:
            log.warning("sketchfab_not_zip", uid=uid)
        except Exception as e:
            log.error("sketchfab_extract_error", uid=uid, error=str(e))

        return None

    def _normalize_model(self, raw: Dict) -> Dict[str, Any]:
        """
        Normalize Sketchfab API response to our schema.

        Key normalizations:
        - tags: API returns [{"name": "sofa", "slug": "sofa"}] → extract name strings
        - thumbnail: best image from thumbnails.images list (pick largest)
        - categories: list of category name strings
        """
        # Extract tag name strings from tag objects
        raw_tags = raw.get("tags", [])
        tags = (
            [t.get("name", "") for t in raw_tags if isinstance(t, dict)]
            if raw_tags and isinstance(raw_tags[0], dict)
            else raw_tags  # already strings (older API)
        )

        # Pick best thumbnail (largest width)
        images = raw.get("thumbnails", {}).get("images", [])
        thumbnail = ""
        if images:
            best = max(images, key=lambda x: x.get("width", 0))
            thumbnail = best.get("url", "")

        return {
            "uid": raw.get("uid"),
            "name": raw.get("name", "Untitled"),
            "description": raw.get("description", ""),
            "thumbnail": thumbnail,
            "author": raw.get("user", {}).get("displayName", "Unknown"),
            "vertex_count": raw.get("vertexCount"),
            "face_count": raw.get("faceCount"),
            "is_downloadable": raw.get("isDownloadable", False),
            "is_restricted": raw.get("isRestricted", False),
            "license": raw.get("license", {}).get("label", "Unknown"),
            "categories": [c.get("name") for c in raw.get("categories", [])],
            "tags": [t for t in tags if t],
            "view_count": raw.get("viewCount", 0),
            "like_count": raw.get("likeCount", 0),
            "price": raw.get("price"),
            "embed_url": raw.get("embedUrl"),
        }

    async def close(self):
        await self.client.aclose()


# ====================================================
# MCP SERVER WRAPPER (optional)
# ====================================================

class SketchfabMCPClient:
    """
    Optional client for a separately-deployed Sketchfab MCP Server.
    Falls back gracefully if not configured.
    """

    def __init__(self, mcp_url: str = None):
        self.mcp_url = mcp_url or config.mcp_server_url
        self.client = (
            httpx.AsyncClient(base_url=self.mcp_url, timeout=60)
            if self.mcp_url else None
        )

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        try:
            resp = await self.client.post("/search", json={"query": query, **kwargs})
            resp.raise_for_status()
            return resp.json().get("results", [])
        except Exception as e:
            log.error("mcp_search_error", error=str(e))
            return []

    async def place_asset(
        self, uid: str, position: Dict[str, float], room: str = None
    ) -> Dict[str, Any]:
        if not self.client:
            return {"error": "MCP not configured"}
        try:
            resp = await self.client.post(
                "/place", json={"uid": uid, "position": position, "room": room}
            )
            return resp.json()
        except Exception as e:
            return {"error": str(e)}


# ====================================================
# UNIFIED MANAGER FACADE
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
        context: str = None,
        max_results: int = 24,
    ) -> List[Dict[str, Any]]:
        """Context-aware search. Appends context to query for better results."""
        enhanced_query = f"{query} {context}" if context else query

        if self.use_mcp:
            results = await self.mcp.search(
                enhanced_query, category=category, max_results=max_results
            )
            if results:
                return results

        return await self.direct.search(
            enhanced_query, category=category, max_results=max_results
        )

    async def get_asset(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get asset metadata + attempt to get download URL + cached path."""
        meta = await self.direct.get_model_details(uid)
        if not meta:
            return None

        # Try to get download URL (requires token + downloadable model)
        download_url = await self.direct.get_download_url(uid)
        meta["download_url"] = download_url

        # Check if already cached
        cache_path = CACHE_DIR / f"{uid}.glb"
        meta["local_path"] = str(cache_path) if cache_path.exists() else None

        return meta

    async def get_or_download(self, uid: str) -> Optional[Path]:
        """Get cached GLB path, downloading and extracting from ZIP if needed."""
        return await self.direct.download_model(uid)

    async def close(self):
        await self.direct.close()


# Global singleton
_sketchfab_manager: Optional[SketchfabManager] = None


def get_sketchfab_manager() -> SketchfabManager:
    global _sketchfab_manager
    if _sketchfab_manager is None:
        _sketchfab_manager = SketchfabManager()
    return _sketchfab_manager
