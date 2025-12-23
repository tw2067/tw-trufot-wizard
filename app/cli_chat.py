from __future__ import annotations
from app.agent.runner import run_turn_stream

def main() -> None:
    history = []
    print("Pharmacy agent CLI. Type 'exit' to quit.\n")

    while True:
        user_text = input("You: ").strip()
        if user_text.lower() in {"exit", "quit"}:
            break

        print("Assistant: ", end="", flush=True)
        gen = run_turn_stream(user_text=user_text, history=history, model="gpt-5")

        try:
            while True:
                ev = next(gen)
                if ev["type"] == "text_delta":
                    print(ev["delta"], end="", flush=True)
                elif ev["type"] == "tool_call":
                    print("\n\n[TOOL CALL]", ev["name"], ev["arguments"])
                    print("Assistant: ", end="", flush=True)
                elif ev["type"] == "tool_result":
                    print("\n[TOOL RESULT]", ev["name"], ev["output"])
                    print("Assistant: ", end="", flush=True)
                elif ev["type"] == "error":
                    print("\n[ERROR]", ev["message"])
                    break
                elif ev["type"] == "done":
                    print("\n")
                    break
        except StopIteration as si:
            history = si.value or history

if __name__ == "__main__":
    main()