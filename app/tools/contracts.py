from __future__ import annotations

from enum import Enum
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, ConfigDict

# You can import enums from your domain models to avoid duplication:
from app.db.models import Language, InteractionLevel

class ContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


##################### error envelope #####################
ToolErrorCode = Literal[
    "MED_NOT_FOUND", "PATIENT_NOT_FOUND", "UNKNOWN_MED_ID",
    "NO_EQUIVALENTS_FOUND", "DB_ERROR", "INVALID_QUERY"
]

class ToolError(ContractBase):
    code: ToolErrorCode = Field(..., examples=["MED_NOT_FOUND", "PATIENT_NOT_FOUND", "DB_ERROR"])
    message: str = Field(..., examples=["Medication not found."])

class ToolResultBase(ContractBase):
    ok: bool = True
    error: Optional[ToolError] = None

##################### structs used across multiple tools #####################
class MedicationInfo(ContractBase):
    med_id: str = Field(..., examples=["MED001"])
    brand_name: str = Field(..., examples=["Advil"])
    generic_name: str = Field(..., examples=["Ibuprofen"])
    active_ingredients: List[str] = Field(..., examples=[["ibuprofen"]])
    form: str = Field(..., examples=["tablet"])
    strength: str = Field(..., examples=["200 mg"])
    rx_required: bool = Field(..., examples=[False])

class StockedMedication(MedicationInfo):
    qty_on_hand: int = Field(..., ge=0, examples=[12])


##################### TOOLS #####################
# TOOL 1: inventory_check
class InventoryCheckInput(ContractBase):
    query: str = Field(..., min_length=1, examples=["Advil", "ibuprofen 200"])
    language: Language = Field(default=Language.he)

class InventoryCheckOutput(ToolResultBase):
    matches: List[StockedMedication] = Field(default_factory=list)
    notes: Optional[str] = None

# TOOL 2: inventory_find_equivalent
class EquivalentDisclosure(ContractBase):
    same_active_ingredients: bool
    same_strength: bool
    same_form: bool
    possible_differences: List[str] = Field(
        default_factory=list,
        examples=[["price", "inactive ingredients", "packaging"]],
    )

class EquivalentOption(StockedMedication):
    disclosure: EquivalentDisclosure

class InventoryFindEquivalentInput(ContractBase):
    med_id: str = Field(..., examples=["MED001"])
    language: Language = Field(default=Language.he)
    require_same_strength: bool = True
    require_same_form: bool = True

class InventoryFindEquivalentOutput(ToolResultBase):
    requested: Optional[StockedMedication] = None
    equivalents: List[EquivalentOption] = Field(default_factory=list)
    notes: Optional[str] = None

# TOOL 3: prescription_verify
class PrescriptionVerifyInput(ContractBase):
    patient_id: str = Field(..., examples=["P001"])
    med_id: str = Field(..., examples=["MED003"])
    intent: Literal["new", "refill"] = Field(..., examples=["refill"])
    language: Language = Field(default=Language.he)


class PrescriptionVerifyOutput(ToolResultBase):
    rx_required: Optional[bool] = None

    patient_found: Optional[bool] = None
    has_valid_rx: Optional[bool] = None

    rx_status: Optional[str] = Field(
        default=None,
        examples=["active", "expired", "refill_pending", "cancelled"],
    )
    expires_at: Optional[str] = Field(
        default=None,
        description="ISO date YYYY-MM-DD",
        examples=["2026-01-15"],
    )
    refills_remaining: Optional[int] = Field(default=None, ge=0)

    next_step: Optional[Literal[
        "request_rx_details",
        "allow_refill_request",
        "cannot_proceed",
    ]] = None

    notes: Optional[str] = None

# TOOL 4: interaction_check
class InteractionPair(ContractBase):
    med_id_a: str
    med_id_b: str
    level: InteractionLevel
    message: str


class InteractionCheckInput(ContractBase):
    med_ids: List[str] = Field(..., min_length=1, examples=[["MED001", "MED004"]])
    language: Language = Field(default=Language.he)


class InteractionCheckOutput(ToolResultBase):
    interaction_level: InteractionLevel = InteractionLevel.none
    pairs: List[InteractionPair] = Field(default_factory=list)
    notes: Optional[str] = None

##################### registry for tool writing #####################
TOOL_REGISTRY = {
    "inventory_check": (InventoryCheckInput, InventoryCheckOutput),
    "inventory_find_equivalent": (InventoryFindEquivalentInput, InventoryFindEquivalentOutput),
    "prescription_verify": (PrescriptionVerifyInput, PrescriptionVerifyOutput),
    "interaction_check": (InteractionCheckInput, InteractionCheckOutput),
}
