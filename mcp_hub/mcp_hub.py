from fastapi import FastAPI, Request
import requests
import os

app = FastAPI(title="MCP-Hub")

# 🔧 Statische Tool-Registry (später dynamisch erweiterbar)
TOOLS = {
    "time": os.getenv("MCP_TIME_URL", "http://host.docker.internal:4210/"),
    "weather": os.getenv("MCP_WEATHER_URL", "http://host.docker.internal:4220/"),
    "docs": os.getenv("MCP_DOCS_URL", "http://host.docker.internal:4230/")
}

@app.get("/")
def root():
    return {"status": "ok", "tools": list(TOOLS.keys())}

@app.get("/manifest")
def manifest():
    return {"tools": TOOLS}

@app.post("/{tool}")
async def route_tool(tool: str, request: Request):
    """Leitet Anfragen an das passende MCP-Tool weiter."""
    if tool not in TOOLS:
        return {"error": f"Unknown tool '{tool}'", "available": list(TOOLS.keys())}

    try:
        data = await request.json()

        # 🔧 Wenn das Tool MCP/JSON-RPC spricht, korrektes Payload bauen
        if tool == "time":
            rpc_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "get_time",
                    "arguments": {}
                }
            }
            response = requests.post(TOOLS[tool], json=rpc_payload, timeout=10)
        else:
            # Standardweiterleitung (z.B. für Weather oder Docs)
            response = requests.post(TOOLS[tool], json=data, timeout=10)

        return response.json()
    except Exception as e:
        return {"error": f"Failed to reach tool '{tool}'", "details": str(e)}
