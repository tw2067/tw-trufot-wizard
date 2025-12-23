from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.agent.runner import run_turn_stream
from app.eval.test_cases import TEST_CASES
from app.eval.checks import assert_contains, assert_not_contains, assert_tools_in_order

MODEL = "gpt-5"

def run_one_case(case: Dict[str, Any]) -> Tuple[bool, List[str]]:
    history: List[Dict[str, Any]] = []
    all_text = ""
    tool_calls: List[str] = []

    for user_turn in case["turns"]:
        gen = run_turn_stream(user_text=user_turn, history=history, model=MODEL)
        try:
            while True:
                ev = next(gen)
                if ev["type"] == "text_delta":
                    all_text += ev["delta"]
                elif ev["type"] == "tool_call":
                    tool_calls.append(ev["name"])
                elif ev["type"] == "error":
                    return False, [f"Runtime error: {ev.get('message')}"]
        except StopIteration as si:
            history = si.value or history

    errors: List[str] = []
    exp = case["expects"]
    assert_tools_in_order(tool_calls, exp.get("tools_in_order", []), errors)
    assert_contains(all_text, exp.get("must_contain", []), errors)
    assert_not_contains(all_text, exp.get("must_not_contain", []), errors)

    return (len(errors) == 0), errors

def main() -> None:
    passed = 0
    for tc in TEST_CASES:
        ok, errors = run_one_case(tc)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {tc['id']}")
        if not ok:
            for e in errors:
                print("  -", e)
        else:
            passed += 1

    print(f"\nSummary: {passed}/{len(TEST_CASES)} passed.")
    if passed != len(TEST_CASES):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
