# 🧩 AnythingLLM Local MCP Framework
A modular, local plugin system that enables **AnythingLLM** to communicate with multiple **MCP servers** running in isolated Docker containers.  
It provides a single, secure HTTP access point while keeping every MCP fully sandboxed and independent.

---

Installation:

`git clone https://github.com/danny0094/mcp-bridge-stack
cd mcp-bridge-stack
docker compose up -d
docker ps
`


## 🚀 Overview

This framework extends AnythingLLM with a **Claude-like local MCP environment**, built entirely with Docker containers.

### ✨ Features
- **Safe & clean:** No host or Docker-in-Docker access.
- **Modular:** Each MCP runs in its own lightweight FastAPI container.
- **Bridge-controlled:** AnythingLLM communicates only with the `mini-bridge`, never directly with MCPs.
- **Dynamic registry:** MCP servers are auto-loaded from `mcp_registry.json`.
- **Auto reload:** Configuration changes are applied live – no container restart required.
- **Example MCPs:** Includes `Dummy-MCP` (handshake test) and a working `MCP-Time` module returning system time.

---

## 🧠 Architecture Diagram

```text
───────────────────────────────────────────────
Docker Network: danny-ai-net
───────────────────────────────────────────────
│
├─ anythingllm  (Port 3001)
│     ↳ Main app (UI + chat logic)
│     ↳ Sends all queries → mini-bridge
│
├─ mini-bridge  (Port 4100)
│     ↳ Central gateway between AnythingLLM and all MCPs
│     ↳ Routes requests via Decision Model
│     ↳ Auto-reloads mcp_registry.json dynamically
│
│     Workflow:
│        User → AnythingLLM → mini-bridge
│              ├─→ Decision-Agent (/route)
│              │      ↳ Decides which MCP to call
│              │      ↳ Returns JSON { "tool": "time" }
│              └─→ Forwards to chosen MCP via MCP-Hub
│
├─ decision-agent (prompt_injector)  (Port 4300)
│     ↳ Lightweight model (Gemma 270M)
│     ↳ Analyses prompt context
│     ↳ Decides when to trigger MCP calls
│     ↳ Responds with structured tool decision
│
├─ mcp-hub  (Port 4400)
│     ↳ Central registry + router for all MCP modules
│     ↳ Provides endpoints:
│          • /list – list all MCPs
│          • /status/<id> – health check
│          • /route – forward via hub
│
├─ dummy-mcp  (Port 4200)
│     ↳ Test MCP – returns handshake / status info
│
├─ mcp-time  (Port 4210)
│     ↳ Returns current UTC or local time via JSON-RPC
│
└─ (future) mcp-docs / mcp-weather / ...
      ↳ Extend system modularly – new MCPs auto-register in hub
───────────────────────────────────────────────
│
└─ Dual Model Flow:
       Decision Model  🧭 (Gemma 270M) → Tool choice
       Main Model      🧠 (Gemma 12B / DeepSeek 8B) → Reasoning + response
───────────────────────────────────────────────
```

---

## ⚙️ File Overview

### `mini_bridge.py`
Core gateway component forwarding AnythingLLM requests to the appropriate MCP.

```python
REGISTRY_PATH = "/app/config/mcp_registry.json"
CHECK_INTERVAL = 3  # seconds for auto reload
```

This file dynamically loads all active MCP servers from `config/mcp_registry.json`.

**Decision forwarding:**
```python
decision = await client.post("http://decision-agent:4300/route", json=payload)
route = decision.json().get("tool", "dummy")  # fallback
```
This defines how the bridge communicates with the Decision-Agent (port 4300 as example).

---

### `mini_prompt_injector.py`
Acts as the **Decision Model Agent**. It intercepts messages and determines which MCP should be triggered.

**Environment variables:**
```python
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/chat")
MCP_HUB_URL = os.getenv("MCP_HUB_URL", "http://host.docker.internal:4000")
```

- `OLLAMA_URL` → your Ollama server (must end with `/api/chat`)
- `MCP_HUB_URL` → internal URL for MCP-Hub access (same network)

**Model configuration:**
```python
DECISION_MODEL = "gemma3:270m"
ANSWER_MODEL   = "gemma3:12b"
```
- **Decision Model** → chooses the right MCP tool.
- **Answer Model** → generates final reasoning and response.

**System prompt:**  
Customizable prompt automatically passed to the Answer Model.  
Use it to define behavioral rules, tone, or response formatting.

---

### `mcp_hub.py`
Central registry and router connecting all MCP servers.

When adding a new MCP container, simply extend the `TOOLS` dictionary:

```python
TOOLS = {
    "time": os.getenv("MCP_TIME_URL", "http://host.docker.internal:4210/"),
    "weather": os.getenv("MCP_WEATHER_URL", "http://host.docker.internal:4220/"),
    "docs": os.getenv("MCP_DOCS_URL", "http://host.docker.internal:4230/")
}
```

Each new entry adds a live MCP endpoint visible via `/list` and `/status`.

---

## 🧩 Dual-Model System

| Layer | Model | Role | Description |
|-------|--------|------|--------------|
| 🧭 Decision Layer | Gemma 3 270M | Routing / Tool selection | Analyzes prompt context and decides which MCP to call |
| 🧠 Main Layer | Gemma 3 12B / DeepSeek R1 8B | Reasoning / Response | Generates the final user-facing answer |

---

## 💡 Example Use Case

> “How late is it?” → AnythingLLM → mini-bridge → Decision-Agent → MCP-Time → Response returned via Main Model.

---

## 🧱 Future Modules

You can easily extend the system with more MCPs:
- `mcp-weather` → fetch local weather data  
- `mcp-docs` → handle document search  
- `mcp-audio` → transcribe or process voice inputs  

Each additional MCP only needs:
1. Its own small FastAPI container.
2. Entry in `mcp_registry.json` or `mcp_hub.py`.
3. Network label in `docker-compose.yml`.

---

## 🧰 Credits & Notes

Built by **Danny** (2025) as a local AnythingLLM extension for modular AI experimentation.  
Inspired by Claude’s MCP design, but built entirely for local, offline use.

---

📄 *For documentation or updates, visit the project’s GitHub page.*
