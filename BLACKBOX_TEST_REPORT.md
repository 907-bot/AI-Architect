# AI Architect Black-Box Test Report

Date: 2026-06-04

## Scope

The project was run locally and tested through localhost-facing behavior:

- Frontend Next.js app
- FastAPI backend
- Redis render queue
- Ollama / Llama 3.1 integration
- Blender binary export path
- Blender MCP HTTP server
- GLB artifact serving
- Artifact pipeline
- Asset library and Sketchfab catalog endpoints
- Core build and backend test gates

## Local Services Verified

| Component | Evidence | Result |
| --- | --- | --- |
| Frontend | `GET http://127.0.0.1:3000` returned `200 OK`, HTML contained `AI Architect` and `prompt-input` | Pass |
| Backend | `GET /health` returned `{"status":"ok"}` | Pass |
| Full stack status | `GET /api/stack-status` returned all components `available: true` | Pass |
| Redis | `redis-cli ping` returned `PONG`; `/api/stack-status.redis.available=true` | Pass |
| Ollama / Llama 3.1 | `/api/ollama-status` returned `available=true`, model `llama3.1:latest` | Pass |
| Blender | `/api/stack-status.blender.available=true`, Blender `5.1.2` | Pass |
| Blender MCP HTTP | `GET http://127.0.0.1:8765/health` returned `status=ok` | Pass |

## Automated Gates

| Gate | Command | Result |
| --- | --- | --- |
| Backend tests | `pytest backend/tests -q` | 55 passed |
| Frontend production build | `npm run build` in `frontend/` | Passed |

## Black-Box API Results

| Area | Endpoint / Flow | Evidence | Result |
| --- | --- | --- | --- |
| OpenAPI | `GET /api/openapi.json` | 83 paths exposed | Pass |
| Styles | `GET /api/styles` | 10 styles returned | Pass |
| House styles | `GET /api/house-styles` | 5 house styles returned | Pass |
| Prompt generation | `POST /api/generate` | Returned `success=true`, `blender_rendered=true`, `glb_path=/exports/house_1780547728078.glb` | Pass |
| Blender GLB artifact | Local file check | GLB exists, size `969960` bytes | Pass |
| GLB serving | `GET /exports/house_1780547728078.glb` | HTTP 200, `content-type: model/gltf-binary`, first bytes `glTF` | Pass |
| Render queue | `POST /api/render-jobs/enqueue`, then `GET /api/render-jobs/{job_id}` | Job queued and readable from Redis | Pass |
| Artifact pipeline | `POST /api/artifacts/generate-progressive` | Status `completed`, produced `floorplan` and `preview` artifacts | Pass |
| Asset materials | `GET /api/assets-library/materials` | 10 materials | Pass |
| Asset furniture | `GET /api/assets-library/furniture` | 9 furniture assets | Pass |
| Asset HDRIs | `GET /api/assets-library/hdris` | 9 HDRIs | Pass |
| Asset resolve | `GET /api/assets-library/resolve?style=contemporary` | Returned materials and HDRI | Pass |
| Sketchfab health | `GET /api/sketchfab/health` | Returned `status=ok` | Pass |
| Sketchfab catalog | `GET /api/sketchfab/catalog/living` | Returned 6 curated items | Pass |

## Browser-Level Results

The in-app browser could load the app through `http://0.0.0.0:3000`.

- Runtime badges displayed green after CORS fix: Ollama, Blender, Redis, MCP.
- Canvas was present.
- A UI-submitted prompt completed and the assistant response stated Blender exported a GLB:
  `/exports/house_1780549087970.glb`.

The long browser automation call timed out while waiting for the full generation loop, but a recovered page state showed the successful assistant response and exported GLB path. API-level artifact checks independently proved GLB export and serving.

## Fixes Made During Testing

- Registered `.glb` and `.gltf` MIME types so browser GLB loaders receive `model/gltf-binary`.
- Fixed Redis render queue serialization so dict/list/None job fields do not crash Redis `hset`.
- Fixed style fallback in `style_engine` so broad styles like `modern` and `contemporary` do not crash asset resolution.
- Reordered Sketchfab dynamic `/{uid}` route so fixed routes like `/health` and `/catalog/{room_type}` are reachable.
- Made Ollama URL/model handling robust when env vars are present but blank.
- Allowed `0.0.0.0` local dev origins through CORS for the in-app browser black-box route.

## Known Limitations / Not Fully Proven

- Database-backed routes remain in no-DB mode because no `DATABASE_URL`/Supabase DB is configured. The backend intentionally reports `database: unavailable (procedural mode)`.
- External Sketchfab live search/download depends on external API/network/token behavior. Local health and curated catalog were verified.
- Browser automation was partially limited by client-side localhost blocking and long generation timeouts. The UI load, service badges, canvas presence, and completed prompt response were verified; artifact correctness was verified through HTTP and filesystem evidence.

