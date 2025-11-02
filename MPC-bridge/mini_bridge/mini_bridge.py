# mini_bridge_v2.py
import json, os, time, asyncio, logging
from fastapi import FastAPI, Request
import httpx
from typing import Dict

app = FastAPI()
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

REGISTRY_PATH = "/app/config/mcp_registry.json"
CHECK_INTERVAL = 3  # Sekunden für Reload-Check

routes: Dict[str, str] = {}
last_mtime: float = 0.0
auto_reload: bool = False


# 🔹 Registry laden
def load_registry():
    global routes, last_mtime, auto_reload
    try:
        mtime = os.path.getmtime(REGISTRY_PATH)
        if mtime == last_mtime:
            return  # Keine Änderung
        last_mtime = mtime

        with open(REGISTRY_PATH, "r") as f:
            data = json.load(f)

        auto_reload = data.get("autoReload", False)
        routes = {srv["id"]: srv["url"] for srv in data.get("servers", []) if srv.get("enabled", True)}

        logging.info(f"[Bridge] Registry reloaded: {list(routes.keys())}")
    except Exception as e:
        logging.error(f"[Bridge] Fehler beim Laden der Registry: {e}")


# 🔹 Hintergrund-Task: Überwacht Dateiänderungen
@app.on_event("startup")
async def watch_registry():
    load_registry()
    async def watcher():
        while True:
            if auto_reload:
                load_registry()
            await asyncio.sleep(CHECK_INTERVAL)
    asyncio.create_task(watcher())


# 🔹 MCP-Request-Weiterleitung
@app.post("/{mcp_id}")
async def handle_request(mcp_id: str, request: Request):
    if mcp_id not in routes:
        return {"error": f"Unknown MCP ID: {mcp_id}", "available": list(routes.keys())}

    try:
        payload = await request.json()
        target_url = routes[mcp_id]

        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, json=payload)
            logging.info(f"[Bridge] Forwarded → {mcp_id} ({response.status_code})")
            return response.json()

    except Exception as e:
        logging.error(f"[Bridge] Fehler bei {mcp_id}: {e}")
        return {"error": str(e)}


# 🧩 Fallback für AnythingLLM (POST / ohne ID)
@app.post("/")
async def handle_default(request: Request):
    if not routes:
        return {"error": "No MCP routes loaded"}

    default_mcp = list(routes.keys())[0]
    target_url = routes[default_mcp]
    payload = await request.json()

    async with httpx.AsyncClient() as client:
        response = await client.post(target_url, json=payload)
        logging.info(f"[Bridge] Default route → {default_mcp} ({response.status_code})")
        return response.json()


# 🔹 Manifest anzeigen
@app.get("/manifest.json")
async def manifest():
    return {"mcp_servers": list(routes.keys()), "autoReload": auto_reload}
