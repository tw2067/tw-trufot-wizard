from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.agent.runner import run_turn_stream

import logging
logger = logging.getLogger("pharmacy_agent.web")

app = FastAPI(title="Pharmacy Agent (Demo)")
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    with open("app/web/static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/chat")
async def chat(req: Request):
    """stateless SSE endpoint"""
    body = await req.json()
    message: str = body.get("message", "")
    history: Optional[List[Dict[str, Any]]] = body.get("history")

    def sse_event(event_type: str, data: Dict[str, Any]) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def stream():
        updated_history: List[Dict[str, Any]] = history or []
        gen = run_turn_stream(user_text=message, history=updated_history, model="gpt-5")

        try:
            while True:
                ev = next(gen)
                if ev["type"] in {"tool_call", "tool_result"}:
                    logger.info("tool_event", extra=ev)
                yield sse_event(ev["type"], ev)
                if ev["type"] == "error":
                    break
        except StopIteration as si:
            updated_history = si.value or updated_history
            yield sse_event("history", {"type": "history", "history": updated_history})

    return StreamingResponse(stream(), media_type="text/event-stream")