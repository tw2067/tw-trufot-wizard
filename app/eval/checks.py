from __future__ import annotations

from dataclasses import dataclass
from typing import List

@dataclass
class EvalResult:
    ok: bool
    errors: List[str]

def assert_contains(text: str, phrases: List[str], errors: List[str]) -> None:
    t = text.lower()
    for p in phrases:
        if p.lower() not in t:
            errors.append(f"Missing required phrase: {p}")

def assert_not_contains(text: str, phrases: List[str], errors: List[str]) -> None:
    t = text.lower()
    for p in phrases:
        if p.lower() in t:
            errors.append(f"Contains prohibited phrase: {p}")

def assert_tools_in_order(calls: List[str], expected: List[str], errors: List[str]) -> None:
    # subsequence check (not necessarily contiguous)
    i = 0
    for c in calls:
        if i < len(expected) and c == expected[i]:
            i += 1
    if i != len(expected):
        errors.append(f"Tool sequence mismatch. Expected subsequence {expected}, got {calls}")
