from __future__ import annotations

from typing import Any, Callable, Dict, Tuple, Type
from pydantic import BaseModel, ValidationError
import logging

from app.tools.contracts import TOOL_REGISTRY, ToolError
from app.tools.inventory import inventory_check, inventory_find_equivalent
from app.tools.prescriptions import prescription_verify
from app.tools.interactions import interaction_check

# map tool name to implementation
TOOL_IMPLS: Dict[str, Callable[[Dict[str, Any]], BaseModel]] = {
    "inventory_check": inventory_check,
    "inventory_find_equivalent": inventory_find_equivalent,
    "prescription_verify": prescription_verify,
    "interaction_check": interaction_check,
}

logger = logging.getLogger("pharmacy_agent.tools")

def dispatch_tool(tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch tool call by name.
    """
    # check the tool exists
    if tool_name not in TOOL_REGISTRY or tool_name not in TOOL_IMPLS:
        logger.error(
            "Unknown tool requested",
            extra={"tool_name": tool_name, "tool_args": tool_args},
        )
        return {
            "ok": False,
            "error": {"code": "UNKNOWN_TOOL", "message": f"Unknown tool: {tool_name}"},
        }

    input_model, output_model = TOOL_REGISTRY[tool_name]  # type: ignore[assignment]
    impl = TOOL_IMPLS[tool_name]

    # validate args
    try:
        validated_in = input_model.model_validate(tool_args)
    except ValidationError as e:
        logger.warning(
            "Tool input validation failed",
            extra={
                "tool_name": tool_name,
                "tool_args": tool_args,
                "validation_error": str(e),
            },
        )
        return {
            "ok": False,
            "error": {"code": "INVALID_TOOL_ARGS", "message": e.__str__()},
        }

    # call implementation
    try:
        out_obj = impl(validated_in.model_dump())
    except Exception as e:
        logger.exception(
            "Tool runtime error",
            extra={
                "tool_name": tool_name,
                "tool_args": validated_in.model_dump(),
            },
        )
        return {
            "ok": False,
            "error": {"code": "TOOL_RUNTIME_ERROR", "message": str(e)},
        }

    # validate output
    try:
        validated_out = output_model.model_validate(out_obj)
    except ValidationError as e:
        logger.critical(
            "Tool output validation failed",
            extra={
                "tool_name": tool_name,
                "raw_output": out_obj,
                "validation_error": str(e),
            },
        )
        return {
            "ok": False,
            "error": {"code": "INVALID_TOOL_OUTPUT", "message": e.__str__()},
        }

    logger.info(
        "Tool executed successfully",
        extra={"tool_name": tool_name},
    )
    return validated_out.model_dump()
