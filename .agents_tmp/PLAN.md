# 1. OBJECTIVE

Connect Blender locally to ChatGPT API by creating an `mcp_config.json` file that defines the Blender MCP server, enabling ChatGPT to invoke Blender 3D generation tools through the existing `backend/blender/mcp_tools.py` server.

# 2. CONTEXT SUMMARY

- **Existing MCP Server**: `backend/blender/mcp_tools.py` uses `fastmcp>=0.4.0` to expose Blender generation tools (`generate_house`, `create_room`, `create_roof`, `export_glb`)
- **AI Stack**: `langchain-openai>=0.3.0` already in requirements
- **ChatGPT**: Supports MCP servers via `mcp_config.json` (desktop app) or API configuration
- **Transport options**: stdio (command-based) or HTTP/SSE (url-based)

# 3. APPROACH OVERVIEW

Create a properly structured `mcp_config.json` that points ChatGPT to the running Blender MCP server:
1. **Local server mode** (recommended): Start server on localhost, point config to HTTP endpoint
2. **Command mode**: Use Python + uvicorn as the command for stdio transport

The MCP config format uses `mcpServers` with either `command` (stdio) or `url` (HTTP/SSE) transport.

# 4. IMPLEMENTATION STEPS

### Step 1: Create `mcp_config.json` at project root
- **Goal**: Create a config file that ChatGPT can use to connect to the Blender MCP server
- **Method**: Create JSON config with server definition using HTTP/SSE transport (more reliable for local dev)
- **Reference**: `backend/blender/mcp_tools.py`

### Step 2: Update MCP server for HTTP transport
- **Goal**: Ensure the server can run as a standalone HTTP service
- **Method**: Verify FastMCP server runs with `uvicorn backend.blender.mcp_tools:mcp_server --reload`
- **Reference**: `backend/blender/mcp_tools.py`

### Step 3: Add startup instructions to README
- **Goal**: Document how to start the server before connecting from ChatGPT
- **Method**: Add a section explaining the setup process

# 5. TESTING AND VALIDATION

- Verify `mcp_config.json` is valid JSON and follows MCP spec
- Confirm server starts: `uvicorn backend.blender.mcp_tools:mcp_server`
- Test connection from ChatGPT desktop app by asking it to use a Blender tool
- Validate end-to-end: prompt → scene graph → 3D model generation
