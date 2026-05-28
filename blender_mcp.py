import mcp

# Set up MCP client connection
client = mcp.MCPClient('localhost', 8080)

# Authenticate (not required in this case)
# client.authenticate('username', 'password')

# Send command to get the current scene
scene_cmd = {'cmd': 'info', 'args': {'type': 'scene'}}
response = client.send_command(scene_cmd)

print(response)