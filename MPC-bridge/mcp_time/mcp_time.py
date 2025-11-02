from fastapi import FastAPI, Request
from datetime import datetime
import json, logging

app = FastAPI()
logging.basicConfig(level=logging.INFO)


@app.post("/")
async def root(request: Request):
    data = await request.json()
    method = data.get("method")

    # AnythingLLM handshake
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": data.get("id", 1),
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {"streaming": False},
                "serverInfo": {"name": "MCP-Time", "version": "1.0.0"}
            }
        }

    # Tool list
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": data.get("id", 1),
            "result": {
                "tools": [
                    {
                        "name": "get_time",
                        "description": "Returns the current system time (ISO format)",
                        "parameters": {}
                    }
                ]
            }
        }

    # Tool call
    if method == "tools/call":
        return {
            "jsonrpc": "2.0",
            "id": data.get("id", 1),
            "result": {
                "time": datetime.utcnow().isoformat() + "Z"
            }
        }

    return {"jsonrpc": "2.0", "error": f"Unknown method: {method}"}


@app.get("/")
async def alive():
    return {"status": "ok", "server": "MCP-Time"}
