from __future__ import annotations
from typing import Any, Dict, List, Type
from pydantic import BaseModel
from app.tools.contracts import TOOL_REGISTRY

TOOL_DESCRIPTIONS: Dict[str, str] = {
    "inventory_check": (
        "Search medications by brand or generic name and return matching items with stock quantity."
    ),
    "inventory_find_equivalent": (
        "Given a medication ID, find identical-equivalent options (same active ingredients, form, strength) "
        "and return disclosure + stock quantities."
    ),
    "prescription_verify": (
        "Verify whether a medication requires a prescription and whether a patient has a valid prescription on file."
    ),
    "interaction_check": (
        "Check interaction rules among a set of medication IDs and return overall interaction level and pair details."
    ),
}

def _pydantic_to_json_schema(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Convert a pydantic model to a json schem.
    """
    schema = model.model_json_schema()
    return schema

def build_openai_function_tools() -> List[Dict[str, Any]]:
    """Build OpenAI Responses API function tools list from TOOL_REGISTRY."""
    tools: List[Dict[str, Any]] = []

    for tool_name, (InputModel, _OutputModel) in TOOL_REGISTRY.items():
        tools.append(
            {
                "type": "function",
                "name": tool_name,
                "description": TOOL_DESCRIPTIONS.get(tool_name, ""),
                "parameters": _pydantic_to_json_schema(InputModel),
            }
        )

    return tools