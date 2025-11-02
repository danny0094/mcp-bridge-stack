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
            return
        last_mtime = mtime

        with open(REGISTRY_PATH, "r") as f:
            data = json.load(f)

        auto_reload = data.get("autoReload", False)
        routes = {srv["id"]: srv["url"] for srv in data.get("servers", []) if srv.get("enabled", True)}

        logging.info(f"[Bridge] Registry reloaded: {list(routes.keys())}")
    except Exception as e:
        logging.error(f"[Bridge] Fehler beim Laden der Registry: {e}")


# 🔹 Hintergrund-Task: Registry überwachen
@app.on_event("startup")
async def watch_registry():
    load_registry()

    async def watcher():
        while True:
            if auto_reload:
                load_registry()
            await asyncio.sleep(CHECK_INTERVAL)

    asyncio.create_task(watcher())


# 🔹 MCP-Request mit direkter Ziel-ID
@app.post("/{mcp_id}")
async def handle_request(mcp_id: str, request: Request):
    if mcp_id not in routes:
        return {"error": f"Unknown MCP ID: {mcp_id}", "available": list(routes.keys())}

    payload = await request.json()
    target_url = routes[mcp_id]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, json=payload)
            logging.info(f"[Bridge] Forwarded → {mcp_id} ({response.status_code})")
            return response.json()
    except Exception as e:
        logging.error(f"[Bridge] Fehler bei {mcp_id}: {e}")
        return {"error": str(e)}


# 🧠 Decision-Agent Routing (AnythingLLM POST /)
@app.post("/")
async def route_via_decision_agent(request: Request):
    payload = await request.json()

    # 1️⃣ Anfrage an Decision-Agent
    async with httpx.AsyncClient() as client:
        try:
            decision = await client.post("http://decision-agent:4300/route", json=payload)
            route = decision.json().get("tool", "dummy")  # fallback
            logging.info(f"[Bridge] Decision-Agent chose: {route}")
        except Exception as e:
            logging.error(f"[Bridge] Decision-Agent Fehler: {e}")
            route = "dummy"

        # 2️⃣ Weiterleiten an passendes MCP
        if route not in routes:
            logging.warning(f"[Bridge] Route '{route}' unbekannt, fallback → dummy")
            route = "dummy"

        target_url = routes.get(route)
        response = await client.post(target_url, json=payload)

        logging.info(f"[Bridge] Final Forward → {route} ({response.status_code})")
        return response.json()


# 🔹 Manifest anzeigen
@app.get("/manifest.json")
async def manifest():
    return {"mcp_servers": list(routes.keys()), "autoReload": auto_reload}
