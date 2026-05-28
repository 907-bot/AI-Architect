<div align="center">
  <img src="https://raw.githubusercontent.com/your-org/ai-architect/main/public/logo.png" alt="AI Architect Logo" width="120" />
  <h1>🏗️ AI ARCHITECT</h1>
  
  <p>
    <strong>AI-native Spatial Architecture Platform</strong><br>
    Generate, visualize, and explore buildings with Multi-Agent AI + 3D Rendering.
  </p>

  <p>
    <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+"></a>
    <a href="https://nodejs.org/"><img src="https://img.shields.io/badge/node-%3E%3D18-green" alt="Node.js 18+"></a>
    <a href="/"><img src="https://img.shields.io/badge/status-production%20ready-brightgreen" alt="Status: Production Ready"></a>
  </p>

  <p>
    <em>Production-ready. Free-tier deployment. Enterprise-grade architecture.</em>
  </p>
</div>

---

## ✨ Features

### 🤖 Multi-Agent AI System
* **Orchestrator Agent**: Master coordinator managing all tasks.
* **Planner Agent**: Interprets architectural requirements.
* **Geometry Agent**: Generates 3D procedural geometry.
* **Asset Agent**: Manages furniture and materials.
* **Bull/Bear/Skeptic Agents**: Evaluate and validate designs.
* **Fallback Chain**: Automatic model switching (DeepSeek → Gemini → Qwen → Llama).

### 🏘️ Scene Generation
* **Text-to-3D**: Natural language to photorealistic 3D buildings.
* **Smart Floorplans**: Floorplan generation with adjacency logic.
* **Procedural Elements**: Room, door, and window generation.
* **Aesthetics**: Material and lighting assignment.
* **Context**: Semantic scene understanding.

### 🎥 Interactive Visualization
* **Real-time 3D**: Browser-based Three.js viewer.
* **Drone Camera**: Cinematic flythroughs.
* **First-Person**: Immersive walkthroughs.
* **Live Sync**: WebSocket real-time updates.
* **History**: Scene version tracking.

### 📊 Enterprise Architecture
* **Standardized**: Canonical scene graph schema.
* **Vector Search**: PostgreSQL + pgvector for semantic search.
* **Secure**: Row-level security (RLS).
* **Auditable**: Comprehensive audit logs.
* **Robust**: Production-grade error handling.

### 🚀 Scalable & Cost-Effective
* **Zero vendor lock-in**: Pure open-source.
* **Free-tier deployment**: Vercel + Railway.
* **Horizontal scaling**: Stateless API design.
* **Cost**: ~$75-85/month for production.

---

## 🚀 Quick Start

### Prerequisites
* Python 3.11+
* Node.js 18+
* Docker & Docker Compose
* API keys: [OpenRouter](#configure-api-keys), [Supabase](#configure-api-keys)

### 1. Clone & Configure

```bash
git clone https://github.com/your-org/ai-architect.git
cd ai-architect
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start Services

**Option A: Docker Compose (Recommended)**
```bash
docker-compose up -d
```

**Option B: Manual Setup**
```bash
# Terminal 1: Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm install && npm run dev
```

### 3. Open Application

* **Frontend:** [http://localhost:3000](http://localhost:3000)
* **API Docs:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
* **WebSocket:** `ws://localhost:8000/ws/{client_id}`

---

## 📋 Configure API Keys

<details>
<summary><strong>OpenRouter (Free AI Models)</strong></summary>

1. Go to [OpenRouter](https://openrouter.ai).
2. Sign up / Log in and get your API key from settings.
3. Add to `.env`: `OPENROUTER_API_KEY=sk-or-v1-...`

*Free tier includes $5 credits, plenty for testing.*
</details>

<details>
<summary><strong>Supabase (PostgreSQL Database)</strong></summary>

1. Go to [Supabase](https://supabase.com).
2. Create a new project and copy connection details.
3. Add to `.env`:
   ```env
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-key
   ```
4. Run schema:
   ```bash
   psql postgresql://user:pass@db.supabase.co/postgres < backend/database/schema.sql
   ```
*Free tier includes 500 MB storage.*
</details>

<details>
<summary><strong>Cloudflare R2 (Object Storage)</strong></summary>

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com).
2. Navigate to R2 → Create bucket.
3. Add to `.env`:
   ```env
   CLOUDFLARE_R2_ACCESS_KEY=your-access-key
   CLOUDFLARE_R2_SECRET_KEY=your-secret-key
   ```
*Free tier includes 10 GB/month.*
</details>

<details>
<summary><strong>Upstash Redis (Cache)</strong></summary>

1. Go to [Upstash](https://upstash.com).
2. Create Redis database and get connection URL.
3. Add to `.env`:
   ```env
   UPSTASH_REDIS_URL=redis://...
   ```
*Free tier includes 10,000 commands/day.*
</details>

---

## 📦 Deployment

**Local Development**
```bash
docker-compose up -d
```

**Production (Vercel + Railway)**
1. **Frontend** → Vercel: `vercel deploy --prod`
2. **Backend** → Railway: `railway login && railway up`
3. **Database** → Supabase (already hosted)

📖 **Full guide**: [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📚 Documentation & Resources

| Resource | Description |
|----------|-------------|
| [**ARCHITECTURE.md**](ARCHITECTURE.md) | System design & data flow |
| [**DEPLOYMENT.md**](DEPLOYMENT.md) | Production deployment guide |
| [**API Docs**](http://localhost:8000/api/docs) | Interactive Swagger UI |
| [**Database Schema**](backend/database/schema.sql) | Raw SQL schema definitions |

---

## 🔐 Security & Performance

**Security**
* **Auth**: JWT tokens (24h expiry), bcrypt hashing, refresh token support.
* **Authorization**: Row-level security (RLS), admin roles.
* **Data**: HTTPS enforced, SQL injection prevention, CORS, Rate limiting (100 req/min).

**Performance**
* **Caching**: Redis caching (1-hour TTL).
* **Optimization**: Database indexing, CDN for static assets, WebSocket compression.
* **Benchmarks**: API < 200ms, Generation 5-30s, Page Load < 2s, WebSocket < 50ms.

---

## 🤝 Support & Community

* **Issues**: [GitHub Issues](https://github.com/your-org/ai-architect/issues)
* **Discussions**: [GitHub Discussions](https://github.com/your-org/ai-architect/discussions)
* **Email**: support@ai-architect.dev
* **Community**: [Discord](https://discord.gg/ai-architect) | [Twitter](https://twitter.com/ai_architect) | [Blog](https://blog.ai-architect.dev)

---

<div align="center">
  <p>Built with ❤️ using FastAPI, Next.js, LangGraph, Three.js, Supabase, and OpenRouter.</p>
  <p><strong>AI Architect</strong> — Empowering creators with spatial intelligence.</p>
</div>

---

## 🔌 MCP Integration (ChatGPT + Blender)

AI Architect supports **Model Context Protocol (MCP)** for seamless integration with ChatGPT and other AI assistants.

### Quick Setup

#### Option 1: Stdio Transport (Recommended for ChatGPT Desktop)

1. **Copy the config file** to your ChatGPT MCP settings directory:
   ```bash
   cp mcp_config.json ~/.config/codeium/mcp_config.json
   # or for Claude/ChatGPT:
   cp mcp_config.json ~/.claude/mcp_config.json
   ```

2. **Start the MCP server** (in a terminal):
   ```bash
   cd /workspace/project/AI-Architect
   PYTHONPATH=/workspace/project/AI-Architect python -m backend.blender.mcp_server
   ```

3. **In ChatGPT**, use the Blender tools to generate houses:
   ```
   "Generate a modern 3-bedroom villa with pool"
   "Add a garage to the current design"
   "Export the model to GLB format"
   ```

#### Option 2: HTTP Transport (For API Clients)

1. **Start the HTTP server**:
   ```bash
   cd /workspace/project/AI-Architect
   PYTHONPATH=/workspace/project/AI-Architect python -m backend.blender.mcp_http_server
   ```

2. **Update mcp_config.json** to point to your server URL:
   ```json
   {
     "mcpServers": {
       "ai-architect-blender-http": {
         "transport": "url",
         "url": "http://YOUR_SERVER_IP:8765"
       }
     }
   }
   ```

3. **Access tools via HTTP API**:
   ```bash
   curl -X POST http://localhost:8765/tools/generate_house \
     -H "Content-Type: application/json" \
     -d '{"scene_graph": {...}, "style": "modern"}'
   ```

### Available MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `generate_house` | Generate complete 3D house | scene_graph, filename, style, render_quality |
| `create_room` | Add room to design | scene_graph, room_name, room_type, dimensions |
| `create_roof` | Add roof structure | scene_graph, roof_style, roof_height |
| `export_glb` | Export to GLB | scene_graph, filename, apply_color_grading |
| `get_scene_info` | Get scene metadata | scene_graph |

### Full Pipeline

```
User Prompt (ChatGPT)
        ↓
Ollama / Llama 3.1 → TOON Script
        ↓
Scene Graph (Rooms, Walls, Doors, Windows)
        ↓
Blender (3D Model with Color Grading)
        ↓
GLB Export → Frontend
        ↓
Web Viewer (Three.js + Interactive Floor Plan)
```

### Example Usage

```python
# Via MCP tools
scene_graph = {
    "house": {
        "name": "modern_villa",
        "style": "modern",
        "rooms": [
            {"name": "living_room", "width": 8, "depth": 6, "height": 3},
            {"name": "bedroom_1", "width": 5, "depth": 5, "height": 3},
            {"name": "kitchen", "width": 4, "depth": 4, "height": 3}
        ]
    }
}

result = generate_house(scene_graph, "villa.glb", style="villa")
# Returns: {"status": "success", "glb_path": "exports/villa.glb", ...}
```

### Troubleshooting

**MCP Server won't start?**
```bash
# Check Python path
export PYTHONPATH=/workspace/project/AI-Architect

# Verify dependencies
pip install fastmcp fastapi uvicorn

# Run with debug
python -m backend.blender.mcp_server --verbose
```

**ChatGPT can't see tools?**
1. Copy `mcp_config.json` to correct location
2. Restart ChatGPT desktop app
3. Check server is running (`curl http://localhost:8765/health`)
