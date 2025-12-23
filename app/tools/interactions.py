from __future__ import annotations

import sqlite3
from typing import Dict, Any, List, Set, Tuple

from app.db.database import get_conn
from app.tools.contracts import (
    InteractionCheckInput,
    InteractionCheckOutput,
    InteractionPair,
    InteractionLevel,
    ToolError,
)

def interaction_check(payload: Dict[str, Any]) -> InteractionCheckOutput:
    """
    Check pairwise interactions among given med_ids.
    - validate all med_ids exist
    - return all interaction_rules where both sides are in med_ids
    - overall level: avoid > caution > none
    """
    inp = InteractionCheckInput.model_validate(payload)
    med_ids = inp.med_ids
    med_set = set(med_ids)

    conn = get_conn()
    try:
        # validate medication existence
        placeholders = ",".join(["?"] * len(med_ids))
        rows = conn.execute(
            f"SELECT med_id FROM medications WHERE med_id IN ({placeholders})",
            tuple(med_ids),
        ).fetchall()
        found = {r["med_id"] for r in rows}
        if found != med_set:
            missing = sorted(list(med_set - found))
            return InteractionCheckOutput(
                ok=False,
                error=ToolError(code="UNKNOWN_MED_ID", message=f"Unknown med_id(s): {missing}"),
                interaction_level=InteractionLevel.none,
                pairs=[],
            )

        # fetch rules where both endpoints are within med_ids
        rule_rows = conn.execute(
            f"""
                    SELECT med_id_a, med_id_b, level, message
                    FROM interaction_rules
                    WHERE med_id_a IN ({placeholders}) AND med_id_b IN ({placeholders})
                    """,
            tuple(med_ids) + tuple(med_ids),
        ).fetchall()

        pairs: List[InteractionPair] = []
        seen_keys: Set[Tuple[str, str]] = set()

        for r in rule_rows:
            a, b = r["med_id_a"], r["med_id_b"]
            key = tuple(sorted((a, b)))
            if key in seen_keys:
                continue
            seen_keys.add(key)

            lvl = InteractionLevel(r["level"])
            pairs.append(
                InteractionPair(
                    med_id_a=a,
                    med_id_b=b,
                    level=lvl,
                    message=r["message"],
                )
        )

        # determine interaction level
        overall = InteractionLevel.none
        if any(p.level == InteractionLevel.avoid for p in pairs):
            overall = InteractionLevel.avoid
        elif any(p.level == InteractionLevel.caution for p in pairs):
            overall = InteractionLevel.caution

        return InteractionCheckOutput(
            ok=True,
            interaction_level=overall,
            pairs=pairs,
            notes=None,
        )

    except sqlite3.Error as e:
        return InteractionCheckOutput(
            ok=False,
            error=ToolError(code="DB_ERROR", message=str(e)),
            interaction_level=InteractionLevel.none,
            pairs=[],
        )

    finally:
        conn.close()