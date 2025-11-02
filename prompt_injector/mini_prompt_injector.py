from fastapi import FastAPI, Request
import requests
import os
import json
import re
import logging

# 🌐 FastAPI Setup
app = FastAPI()

# 🧠 Logging konfigurieren
logging.basicConfig(level=logging.INFO, format="🧩 [%(levelname)s] %(message)s")

# 🔧 Environment Variables
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/chat")
MCP_HUB_URL = os.getenv("MCP_HUB_URL", "http://host.docker.internal:4000")

# 💡 Modelle definieren
DECISION_MODEL = "gemma3:270m"
ANSWER_MODEL = "gemma3:12b"

# 🧩 Systemprompt
SYSTEM_PROMPT = """
You are a routing model in a modular AI architecture.
You receive user input and decide whether it requires a specific tool.

Always output valid JSON like this:
{"action":"mcp_call","tool":"<toolname>","query":"<original user query>"}

Available tools: time, docs, weather.
If none apply, respond with {"action":"none"}.

Rules:
- Never invent data.
- Never explain.
- Only output JSON.
- Keep user query language as-is.
"""

@app.post("/api/generate")
async def inject_prompt(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")

    logging.info(f"💬 Eingabe: {prompt}")

    # 1️⃣ Decision Phase
    decision_payload = {
        "model": DECISION_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": prompt}
        ]
    }

    logging.info(f"🤔 Sende an Decision Model ({DECISION_MODEL}) …")

    decision_resp = requests.post(OLLAMA_URL, json=decision_payload, stream=True)
    decision_text = ""
    for chunk in decision_resp.iter_lines():
        if not chunk:
            continue
        line = chunk.decode() if isinstance(chunk, bytes) else chunk
        try:
            obj = json.loads(line)
            if "message" in obj and "content" in obj["message"]:
                decision_text += obj["message"]["content"]
        except Exception:
            continue

    logging.info(f"📥 Decision Output: {decision_text.strip()}")

    # 🧩 2️⃣ Prüfen auf MCP-Call
    if "mcp_call" in decision_text:
        logging.info("🧠 MCP-Call erkannt → leite an MCP-Hub weiter")

        # Entferne Markdown-Wrapper
        cleaned = re.sub(r"```json|```", "", decision_text, flags=re.IGNORECASE).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logging.error(f"❌ JSON Parse Fehler: {e}")
            return {
                "error": "Decision model did not return valid JSON.",
                "raw_decision": decision_text,
                "cleaned_attempt": cleaned
            }

        tool_name = parsed.get("tool")
        query = parsed.get("query", prompt)
        bridge_url = f"{MCP_HUB_URL}/{tool_name}"

        logging.info(f"🔗 Rufe MCP-Tool '{tool_name}' über {bridge_url} auf")

        tool_response = requests.post(bridge_url, json={"query": query}).json()
        result = tool_response.get("result", tool_response)

        logging.info(f"🧾 MCP-Ergebnis: {result}")

        # 🧠 Antwortmodell formuliert
        answer_payload = {
            "model": ANSWER_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": f"You are the reasoning model. Convert tool outputs into natural answers. "
                               f"The tool '{tool_name}' returned this result: {json.dumps(result, ensure_ascii=False)}"
                },
                {"role": "user", "content": query}
            ]
        }

        logging.info(f"🧩 Sende Ergebnis an {ANSWER_MODEL} …")

        # 🔄 Streaming-Antwort sammeln
        answer_resp = requests.post(OLLAMA_URL, json=answer_payload, stream=True)
        text_out = ""
        for chunk in answer_resp.iter_lines(decode_unicode=True):
            if not chunk:
                continue
            try:
                obj = json.loads(chunk)
                if "message" in obj and "content" in obj["message"]:
                    text_out += obj["message"]["content"]
                if obj.get("done"):
                    break
            except Exception:
                continue

        logging.info(f"✅ Finale Antwort: {text_out.strip()}")

        return {
            "decision": parsed,
            "bridge_result": result,
            "final": text_out.strip()
        }

    # 3️⃣ Kein MCP – direkt Antwortmodell
    logging.info("➡️ Kein MCP-Call, normale Antwort folgt")

    answer_payload = {
        "model": ANSWER_MODEL,
        "messages": [
            {"role": "system", "content": "Beantworte die Frage klar und präzise."},
            {"role": "user", "content": prompt}
        ]
    }

    answer_resp = requests.post(OLLAMA_URL, json=answer_payload, stream=True)
    text_out = ""

    for chunk in answer_resp.iter_lines(decode_unicode=True):
        if not chunk:
            continue
        try:
            obj = json.loads(chunk)
            if "message" in obj and "content" in obj["message"]:
                text_out += obj["message"]["content"]
            if obj.get("done"):
                break
        except Exception:
            continue

    logging.info(f"🧾 Normale Antwort: {text_out.strip()}")

    return {"final": text_out.strip()}
