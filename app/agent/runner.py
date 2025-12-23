from __future__ import annotations

import json
from typing import Any, Dict, Generator, List, Optional
import re

from openai import OpenAI

from app.agent.system_prompt import SYSTEM_PROMPT
from app.agent.tool_schemas import build_openai_function_tools
from app.tools.dispatcher import dispatch_tool

AgentEvent = Dict[str, Any]
InputItem = Dict[str, Any]

HEBREW_CHARS_RE = re.compile(r"[\u0590-\u05FF]")
HEBREW_ADVICE_RE = re.compile(
    r"(מה\s*(כדאי|מומלץ)\s*לקחת|מה\s*לקחת|כאב|כאבים|בחזה|תסמינים|כואב)",
    re.UNICODE,
)

HEBREW_REFUSAL_TEXT = (
    "אני לא יכול/ה לתת ייעוץ רפואי או להמליץ מבחינה רפואית.\n"
    "פנה/י לאיש מקצוע רפואי או לרופא/ה לקבלת הנחיה מתאימה."
)


def _extract_function_calls(response_obj: Any) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    for item in getattr(response_obj, "output", []) or []:
        if getattr(item, "type", None) == "function_call":
            calls.append(
                {
                    "call_id": item.call_id,
                    "name": item.name,
                    "arguments": item.arguments,  # JSON string
                }
            )
    return calls


def run_turn_stream(
    *,
    user_text: str,
    history: Optional[List[InputItem]] = None,  # JSON-safe history ONLY
    model: str = "gpt-5",
) -> Generator[AgentEvent, None, List[InputItem]]:
    """
    Multi-step tool calling with streaming (Responses API), while keeping returned history JSON-serializable.

    - runtime_input: internal list passed to OpenAI; may include SDK objects (NOT JSON)
    - client_history: returned to UI; must remain JSON-safe (role/content only)

    Includes a deterministic Hebrew safety gate for advice-like symptom requests.
    """
    # JSON-safe history from client
    client_history: List[InputItem] = list(history or [])
    client_history.append({"role": "user", "content": user_text})

    if HEBREW_CHARS_RE.search(user_text) and HEBREW_ADVICE_RE.search(user_text):
        yield {"type": "text_delta", "delta": HEBREW_REFUSAL_TEXT}
        client_history.append({"role": "assistant", "content": HEBREW_REFUSAL_TEXT})
        yield {"type": "done"}
        return client_history

    client = OpenAI()
    tools = build_openai_function_tools()

    runtime_input: List[Any] = list(client_history)

    assistant_text_accum = ""

    while True:
        response_obj = None
        try:
            stream = client.responses.create(
                model=model,
                instructions=SYSTEM_PROMPT,
                tools=tools,
                input=runtime_input,
                stream=True,
            )

            for event in stream:
                etype = getattr(event, "type", None)

                if etype == "response.output_text.delta":
                    assistant_text_accum += event.delta
                    yield {"type": "text_delta", "delta": event.delta}

                elif etype == "response.refusal.delta":
                    assistant_text_accum += event.delta
                    yield {"type": "text_delta", "delta": event.delta}

                elif etype == "response.completed":
                    response_obj = event.response

                elif etype == "error":
                    yield {"type": "error", "message": str(getattr(event, "error", event))}
                    return client_history

            if response_obj is None:
                yield {"type": "error", "message": "No completed response received."}
                return client_history

        except Exception as e:
            yield {"type": "error", "message": f"OpenAI call failed: {e}"}
            return client_history

        runtime_input += response_obj.output

        calls = _extract_function_calls(response_obj)
        if not calls:
            client_history.append({"role": "assistant", "content": assistant_text_accum})
            yield {"type": "done"}
            return client_history

        # Execute each function call in order
        for call in calls:
            name = call["name"]
            call_id = call["call_id"]
            args_json = call["arguments"] or "{}"

            # Parse args JSON
            try:
                args = json.loads(args_json)
            except json.JSONDecodeError:
                tool_out = {
                    "ok": False,
                    "error": {"code": "INVALID_TOOL_ARGS", "message": "Could not parse tool arguments JSON."},
                }
                yield {"type": "tool_call", "name": name, "call_id": call_id, "arguments": args_json}
                yield {"type": "tool_result", "name": name, "call_id": call_id, "output": tool_out}

                runtime_input.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(tool_out),
                    }
                )
                continue

            yield {"type": "tool_call", "name": name, "call_id": call_id, "arguments": args}

            tool_out = dispatch_tool(name, args)

            yield {"type": "tool_result", "name": name, "call_id": call_id, "output": tool_out}

            # Feed tool output back to the model (canonical tool flow)
            runtime_input.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(tool_out),
                }
            )