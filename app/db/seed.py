from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from app.db.database import get_conn

SCHEMA_PATH = "app/db/schema.sql"

def iso(d: date) -> str:
    return d.isoformat()

def iso_dt(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()

def norm_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)

def run_seed() -> None:
    conn = get_conn()
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

        patients = [
            ("P001", "גולדה מאיר", "he"),
            ("P002", "Rosalind Franklin", "en"),
            ("P003", "חנה סנש", "he"),
            ("P004", "Marie Curie", "en"),
            ("P005", "לאה גולדברג", "he"),
            ("P006", "Rosa Parks", "en"),
            ("P007", "עדה יונת", "he"),
            ("P008", "Amelia Earhart", "en"),
            ("P009", "נעמי שמר", "he"),
            ("P010", "Henrietta Lacks", "en"),
        ]
        conn.executemany(
            "INSERT INTO patients(patient_id, display_name, language_preference) VALUES (?,?,?)",
            patients,
        )

        meds = [
            {
                "med_id": "MED001",
                "brand_name": "PainAway",
                "generic_name": "Ibuprofen",
                "active_ingredients": ["ibuprofen"],
                "form": "tablet",
                "strength": "200 mg",
                "rx_required": 0,
                "standard_instructions": "Informational only. Follow the product label or a licensed professional’s directions.",
                "common_side_effects": ["nausea", "heartburn"],
                "warnings": ["Informational only. See label for warnings and contraindications."],
            },

            {
                "med_id": "MED002",
                "brand_name": "IbuTabs",
                "generic_name": "Ibuprofen",
                "active_ingredients": ["ibuprofen"],
                "form": "tablet",
                "strength": "200 mg",
                "rx_required": 0,
                "standard_instructions": "Informational only. Follow the product label or a licensed professional’s directions.",
                "common_side_effects": ["nausea", "heartburn"],
                "warnings": ["Informational only. See label for warnings and contraindications."],
            },
            {
                "med_id": "MED003",
                "brand_name": "Cholesto",
                "generic_name": "Atorvastatin",
                "active_ingredients": ["atorvastatin"],
                "form": "tablet",
                "strength": "20 mg",
                "rx_required": 1,
                "standard_instructions": "Prescription only. Use exactly as written on the prescription label.",
                "common_side_effects": ["muscle aches"],
                "warnings": ["Prescription medication. Consult a licensed professional for questions."],
            },
            {
                "med_id": "MED004",
                "brand_name": "AcidEase",
                "generic_name": "Omeprazole",
                "active_ingredients": ["omeprazole"],
                "form": "capsule",
                "strength": "20 mg",
                "rx_required": 0,
                "standard_instructions": "Informational only. Follow the product label or a licensed professional’s directions.",
                "common_side_effects": ["headache"],
                "warnings": ["Informational only. See label for warnings and contraindications."],
            },
            {
                "med_id": "MED005",
                "brand_name": "AllerFree",
                "generic_name": "Loratadine",
                "active_ingredients": ["loratadine"],
                "form": "tablet",
                "strength": "10 mg",
                "rx_required": 0,
                "standard_instructions": "Informational only. Follow the product label or a licensed professional’s directions.",
                "common_side_effects": ["drowsiness"],
                "warnings": ["Informational only. See label for warnings and contraindications."],
            },
        ]

        conn.executemany(
            """
            INSERT INTO medications(
              med_id, brand_name, generic_name, active_ingredients, form, strength,
              rx_required, standard_instructions, common_side_effects, warnings
            )
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            [
                (
                    m["med_id"],
                    m["brand_name"],
                    m["generic_name"],
                    json.dumps(m["active_ingredients"]),
                    m["form"],
                    m["strength"],
                    m["rx_required"],
                    m["standard_instructions"],
                    json.dumps(m["common_side_effects"]),
                    json.dumps(m["warnings"]),
                )
                for m in meds
            ],
        )


        inventory = [
            ("MED001", 0, 5, "A1-01"),
            ("MED002", 25, 5, "A1-02"),
            ("MED003", 10, 2, "B2-01"),
            ("MED004", 18, 3, "C1-03"),
            ("MED005", 30, 5, "C1-04"),
        ]
        conn.executemany(
            "INSERT INTO inventory(med_id, qty_on_hand, reorder_threshold, location_bin) VALUES (?,?,?,?)",
            inventory,
        )

        today = date.today()
        prescriptions = [
            (
                "RX0001",
                "P001",
                "MED003",
                "active",
                iso(today + timedelta(days=180)),
                2,
                "Take as directed on the prescription label.",
                iso_dt(datetime.now(timezone.utc) - timedelta(days=30)),
            ),
            (
                "RX0002",
                "P002",
                "MED003",
                "expired",
                iso(today - timedelta(days=10)),
                0,
                "Take as directed on the prescription label.",
                None,
            ),
        ]
        conn.executemany(
            """
            INSERT INTO prescriptions(
              rx_id, patient_id, med_id, status, expires_at, refills_remaining, directions, last_filled_at
            )
            VALUES (?,?,?,?,?,?,?,?)
            """,
            prescriptions,
        )

        interactions = []

        a, b = norm_pair("MED001", "MED003")
        interactions.append(
            (
                "INT0001",
                a,
                b,
                "avoid",
                "Synthetic demo warning: these two items are flagged as 'do not take together'. Consult a pharmacist/clinician.",
                "synthetic_demo",
            )
        )

        a, b = norm_pair("MED004", "MED005")
        interactions.append(
            (
                "INT0002",
                a,
                b,
                "caution",
                "Synthetic demo warning: interaction flagged as 'caution'. Consult a pharmacist/clinician.",
                "synthetic_demo",
            )
        )

        conn.executemany(
            """
            INSERT INTO interaction_rules(rule_id, med_id_a, med_id_b, level, message, source)
            VALUES (?,?,?,?,?,?)
            """,
            interactions,
        )

        conn.commit()
        print("Seed completed: pharmacy.db created and populated.")
    finally:
        conn.close()


if __name__ == "__main__":
    run_seed()
