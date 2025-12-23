from __future__ import annotations

import sqlite3
from datetime import date
from typing import Dict, Any

from app.db.database import get_conn
from app.tools.contracts import (
    PrescriptionVerifyInput,
    PrescriptionVerifyOutput,
    ToolError,
)

def prescription_verify(payload: Dict[str, Any]) -> PrescriptionVerifyOutput:
    """
    Verify if a prescription is required and whether the patient has a valid prescription.
    - patient must exist in the database
    - medication must exist in the database
    - if rx_required == False -> allow_refill_request
    - if rx_required == True ->:
        status must be 'active'
        expires_at >= today
        if intent == 'refill': refills_remaining > 0
    """
    inp = PrescriptionVerifyInput.model_validate(payload)
    today = date.today().isoformat()

    conn = get_conn()
    try:
        # check medication exists
        m = conn.execute(
            "SELECT rx_required FROM medications WHERE med_id = ?",
            (inp.med_id,),
        ).fetchone()
        if m is None:
            return PrescriptionVerifyOutput(
                ok=False,
                error=ToolError(code="MED_NOT_FOUND", message="Medication not found."),
                patient_found=True,
            )

        # check prescription requirements
        rx_required = bool(m["rx_required"])
        if not rx_required:
            return PrescriptionVerifyOutput(
                ok=True,
                rx_required=False,
                patient_found=True,
                has_valid_rx=None,
                next_step="allow_refill_request",
                notes="No prescription required for this medication.",
            )

        # check patient exists
        p = conn.execute(
            "SELECT 1 FROM patients WHERE patient_id = ?",
            (inp.patient_id,),
        ).fetchone()
        if p is None:
            return PrescriptionVerifyOutput(
                ok=False,
                error=ToolError(code="PATIENT_NOT_FOUND", message="Patient not found."),
                patient_found=False,
            )

        # if prescription required look up prescriptions
        rx = conn.execute(
            """
            SELECT status, expires_at, refills_remaining
            FROM prescriptions
            WHERE patient_id = ?
              AND med_id = ?
            ORDER BY expires_at DESC LIMIT 1
            """,
            (inp.patient_id, inp.med_id),
        ).fetchone()

        # has no prescription
        if rx is None:
            return PrescriptionVerifyOutput(
                ok=True,
                rx_required=True,
                patient_found=True,
                has_valid_rx=False,
                rx_status=None,
                expires_at=None,
                refills_remaining=None,
                next_step="cannot_proceed",
                notes="No prescription on file.",
            )

        # has prescription
        status = rx["status"]
        expires_at = rx["expires_at"]
        refills_remaining = int(rx["refills_remaining"])

        valid = (status == "active") and (expires_at >= today)
        if inp.intent == "refill":
            valid = valid and (refills_remaining > 0)

        return PrescriptionVerifyOutput(
            ok=True,
            rx_required=True,
            patient_found=True,
            has_valid_rx=bool(valid),
            rx_status=status,
            expires_at=expires_at,
            refills_remaining=refills_remaining,
            next_step="allow_refill_request" if valid else "cannot_proceed",
            notes=None,
        )

    except sqlite3.Error as e:
        return PrescriptionVerifyOutput(
        ok=False,
        error=ToolError(code="DB_ERROR", message=str(e)),
        )

    finally:
        conn.close()