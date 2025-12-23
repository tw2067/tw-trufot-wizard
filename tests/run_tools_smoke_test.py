from app.tools.inventory import inventory_check, inventory_find_equivalent
from app.tools.prescriptions import prescription_verify
from app.tools.interactions import interaction_check

print("inventory_check:", inventory_check({"query": "PainAway", "language": "en"}).model_dump())
print("inventory_find_equivalent:", inventory_find_equivalent({"med_id": "MED001", "language": "en"}).model_dump())
print("prescription_verify P001:", prescription_verify({"patient_id": "P001", "med_id": "MED003", "intent": "refill", "language": "en"}).model_dump())
print("prescription_verify P002:", prescription_verify({"patient_id": "P002", "med_id": "MED003", "intent": "refill", "language": "en"}).model_dump())
print("interaction_check:", interaction_check({"med_ids": ["MED001", "MED003"], "language": "en"}).model_dump())
