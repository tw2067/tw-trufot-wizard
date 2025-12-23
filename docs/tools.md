This document defines the tool contracts used by the pharmacy conversational agent.
Tools are executed by the backend; the LLM may only request tool calls with JSON arguments matching the schemas.

## Rules

Global rules:
* Tools return factual, database-backed information only
* The agent must not provide medical advice, diagnosis, or encouragement to purchase
* For advice-seeking questions agent must refuse and redirect to a healthcare professional
* For prescription medications, the agent must verify prescription requirements before proceeding with any processing
* For availability, the agent must check inventory before confirming fulfillment
* For multiple medications, the agent must run interaction check and provide an additional warning when relevant

All tool outputs follow a common structure:
* Success: `"ok": True, "error": None`
* Failure: `"ok": False, "error": {"code": "...", "message": "..."}`

Tool selection rules:
* If the user asks about availability -> call `inventory_check`
* If requested medication is out of stock -> call `inventory_find_equivalent` and disclose differences
* If user requests a refill or any prescription fulfillment -> call `prescription_verify` before submitting/confirming
* If user requests 2 or more medications -> call `interaction_check`
* If user asks for medical advice/diagnosis -> no tool calls, refuse and redirect


## Tools

`inventory_check`:
* Purpose - Search medications by brand/generic name and return matching items with stock quantities
* When is called by agent? - Any request that depends on stock availability (including refill requests)
* Input - ```{
  "query": "string",
  "language": "he|en"
}```
* Output - ```{
  "ok": True,
  "error": None,
  "matches": [
    {
      "med_id": "string",
      "brand_name": "string",
      "generic_name": "string",
      "active_ingredients": ["string"],
      "form": "string",
      "strength": "string",
      "rx_required": True,
      "qty_on_hand": 0
    }
  ],
  "notes": "string|None"
}```
* Error codes - 
  * `MED_NOT_FOUND` - no matching medication in DB
  * `DB_ERROR` - database failure
* Fallback behavior - 
  * `MED_NOT_FOUND` - ask the user to confirm spelling or provide alternatives (brand/generic)
  * Multiple matches - ask user to choose by form/strength
  * If `qty_on_hand == 0` (out of stock) - proceed to `inventory_find_equivalent` (only if user wants a substitute)

`inventory_find_equivalent`:
* Purpose - If a requested medication is out of stock, return identical-equivalent options (same active ingredients, same form, same strength) manufactured by other brands
* When is called by agent? - Only if `inventory_check` shows `qty_on_hand == 0` or the user explicitly requests for equivalents for the requested medication
* Input - ```{
  "med_id": "string",
  "language": "he|en",
  "require_same_strength": True,
  "require_same_form": True
}```
* Output - ```{
  "ok": True,
  "error": None,
  "requested": {
    "med_id": "string",
    "brand_name": "string",
    "generic_name": "string",
    "active_ingredients": ["string"],
    "form": "string",
    "strength": "string",
    "rx_required": True,
    "qty_on_hand": 0
  },
  "equivalents": [
    {
      "med_id": "string",
      "brand_name": "string",
      "generic_name": "string",
      "active_ingredients": ["string"],
      "form": "string",
      "strength": "string",
      "rx_required": True,
      "qty_on_hand": 12,
      "disclosure": {
        "same_active_ingredients": True,
        "same_strength": True,
        "same_form": True,
        "possible_differences": ["price", "inactive ingredients", "packaging"]
      }
    }
  ],
  "notes": "string|None"
}```
* Error codes - 
  * `MED_NOT_FOUND`
  * `NO_EQUIVALENTS_FOUND`
  * `DB_ERROR`
* Fallback behavior - 
  * `NO_EQUIVALENTS_FOUND` - inform user it’s out of stock and no identical-equivalent is available; suggest contacting pharmacy staff
  * Agent must include full disclosure: equivalence is based on active ingredients/form/strength; other differences may exist

`prescription_verify`:
* Purpose - Confirm whether a medication requires a prescription and whether the user has a valid prescription on file for refill workflows
* When is called by agent? - Any refill or fulfillment request or step involving prescription medication
* Input - ```{
  "patient_id": "string",
  "med_id": "string",
  "intent": "new|refill",
  "language": "he|en"
}```
* Output - ```{
  "ok": True,
  "error": None,
  "rx_required": True,
  "patient_found": True,
  "has_valid_rx": False,
  "rx_status": "active|expired|refill_pending|cancelled|None",
  "expires_at": "YYYY-MM-DD|None",
  "refills_remaining": 0,
  "next_step": "request_rx_details|allow_refill_request|cannot_proceed",
  "notes": "string|None"
}```
* Error codes - 
  * `PATIENT_NOT_FOUND`
  * `MED_NOT_FOUND`
  * `DB_ERROR`
* Fallback behavior - 
  * `PATIENT_NOT_FOUND` - ask the user to verify patient id
  * If `rx_required==true` and `has_valid_rx==false` - do not proceed, redirect to a clinician for prescription

`interaction_check`:
* Purpose - Detect interactions among requested medications and produce an additional warning if any pair is marked “avoid”
* When is called by agent? - User requests multiple medications
* Input - ```{
  "med_ids": ["string"],
  "language": "he|en"
}```
* Output - {
  "ok": True,
  "error": None,
  "interaction_level": "none|caution|avoid",
  "pairs": [
    {
      "med_id_a": "string",
      "med_id_b": "string",
      "level": "caution|avoid",
      "message": "string"
    }
  ],
  "notes": "string|None"
}
* Error codes - 
  * `UNKNOWN_MED_ID`
  * `DB_ERROR`
* Fallback behavior
  * `UNKNOWN_MED_ID` - agent must state it cannot assess interactions for unknown items and redirect to a pharmacist/clinician
  * `interaction_level==avoid` - agent must add an explicit “cannot be taken together” warning and refuse to advise what action to take