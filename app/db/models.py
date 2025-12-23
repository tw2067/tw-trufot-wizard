from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


##################### enums and helpers #####################
class Language(str, Enum):
    he = "he"
    en = "en"

class RxStatus(str, Enum):
    active = "active"
    refill_pending = "refill_pending"
    expired = "expired"
    cancelled = "cancelled"

class InteractionLevel(str, Enum):
    none = "none"
    caution = "caution"
    avoid = "avoid"


##################### base model config #####################
class AppBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")  # unknown fields are rejected

##################### entities #####################
class User(AppBaseModel):
    user_id: str = Field(..., examples=["P001"])  # p for patient
    full_name: str = Field(..., examples=["Rosalind Franklin", "גולדה מאיר"])
    language_preference: Language = Field(default=Language.he)  # Ivri daber Ivrit :)

class Medication(AppBaseModel):
    med_id: str = Field(..., examples=["MED001"])
    brand_name: str = Field(..., examples=["Advil"])
    generic_name: str = Field(..., examples=["Ibuprofen"])
    active_ingredients: List[str] = Field(..., examples=[["ibuprofen"]])

    form: str = Field(..., examples=["tablet", "capsule", "syrup"])
    strength: str = Field(..., examples=["200 mg", "10 mg/5 mL"])

    rx_required: bool = Field(..., description="True if prescription is required")

    standard_instructions: str = Field(
        ...,
        description="General usage instruction as provided on label; informational only!"
    )

    common_side_effects: List[str] = Field(
        default_factory=list,
        description="Short list of common side effects; informational only!"
    )

    warnings: List[str] = Field(
        default_factory=list,
        description="High-level warnings/contraindications; informational, non-personalized"
    )

class InventoryItem(AppBaseModel):
    med_id: str
    qty_on_hand: int = Field(..., ge=0)
    reorder_threshold: int = Field(default=0, ge=0)
    location_bin: Optional[str] = Field(default=None, examples=["A3-02"])

class Prescription(AppBaseModel):
    rx_id: str = Field(..., examples=["RX1001"])
    user_id: str = Field(..., examples=["P001"])
    med_id: str = Field(..., examples=["MED001"])

    status: RxStatus = Field(default=RxStatus.active)
    expires_at: date
    refills_remaining: int = Field(default=0, ge=0)

    directions: str = Field(
        ...,
        description="Directions as written on prescriptions. Do not reinterpret"
    )

    last_filled_at: Optional[datetime] = None

##################### Interaction rules #####################
class InteractionRule(AppBaseModel):
    rule_id: str = Field(..., examples=["INT001"])
    med_id_a: str = Field(..., examples=["MED001"])
    med_id_b: str = Field(..., examples=["MED004"])

    level: InteractionLevel = Field(default=InteractionLevel.caution)

    # Stored in English; UI/agent can translate
    message: str = Field(
        ...,
        description="Factual warning text. Must not provide medical advice."
    )

    source: Optional[str] = Field(
        default=None,
        description="Optional reference label/source name (e.g., 'FDA label)"
    )

##################### lookup views #####################
class InventoryMatch(AppBaseModel):
    med_id: str
    brand_name: str
    generic_name: str
    strength: str
    rx_required: bool
    qty_on_hand: int

class InventoryCheckResult(AppBaseModel):
    matches: List[InventoryMatch] = Field(default_factory=list)
    in_stock: bool = False
    substitutes: List[InventoryMatch] = Field(default_factory=list)
    notes: Optional[str] = None