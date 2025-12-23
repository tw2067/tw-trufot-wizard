# TW Trufot Wizard - Pharmacy Agent

A **stateless**, real-time conversational pharmacy assistant,
with Python backend, and tool-driven workflows for prescription verification, inventory, and interactions.

* Hebrew + English 
* Streaming (SSE)
* Tool calling + multi-step workflows
* Synthetic database (10 patients, 5 medications)  
* Safety: no diagnosis, no medical advice, no encouragement to purchase

---
## Safety Policy
The agent is **informational only**:
* Allowed: factual medication info (active ingredients, prescription requirement, general label-style instructions, side effects, warnings), stock status, prescription validation, interaction warning
* Prohibited: diagnosis, treatment recommendations, personalized dosing, symptom interpretation, encouragement to purchase.
* If advice is requested, the agent **refuses and redirects** to a licensed professional.

---
## Architecture
* The backend does **not** store sessions.
* The client sends `history` (conversation messages) with each request.
* The server returns updated JSON-safe history for the client to store.

---
## Tools
Tool contracts are defined in `app/tools/contracts.py`, and implemented in `app/tools/*`.

* `inventory_check(query, language)` -> match medications + stock
* `inventory_find_equivalent(med_id, require_same_strength, require_same_form, language)` -> identical-equivalent substitutions with disclosure
* `prescription_verify(patient_id, med_id, intent, language)` -> prescription requirement + patient prescription status
* `interaction_check(med_ids, language)` -> interaction level + flagged pairs

See: `app/docs/tools.md`

NOTE: I added finding equivalent and interaction check services to support better customer service and more complete information.

---
## Multi-step Flows
### Flow 1 - out of stock -> equivalent substitution
1. `inventory_check("...")`
2. If qty_on_hand == 0 -> `inventory_find_equivalent(med_id)`
3. Assistant discloses equivalence and **possible differences** (price / inactive ingredients / packaging)

### Flow 2 - refill workflow
1. `inventory_check("...")`
2. If requires prescription `prescription_verify(patient_id, med_id, intent="refill")`
3. Assistant confirms requirements and availability (no advice)

### Flow 3 - interaction warning for multiple meds
1. Identify meds (inventory lookup)
2. `interaction_check([med_id...])`
3. If avoid -> explicit warning: cannot be taken together and consult a clinician

see `app/eval` for evaluation

---
## Run with Docker
```bash
docker build -t tw-trufot-wizard .
docker run --rm -p 8000:8000 -e OPENAI_API_KEY=YOUR_KEY tw-trufot-wizard
```
open: http://localhost:8000
