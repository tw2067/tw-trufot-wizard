from __future__ import annotations

import json
import sqlite3
from typing import Dict, Any, List

from app.db.database import get_conn
from app.tools.contracts import (
    InventoryCheckInput,
    InventoryCheckOutput,
    InventoryFindEquivalentInput,
    InventoryFindEquivalentOutput,
    StockedMedication,
    EquivalentDisclosure,
    EquivalentOption,
    ToolError,
)
import re

_STOPWORDS = {
    "mg", "g", "mcg", "ml",
    "tablet", "tablets", "tab", "tabs",
    "capsule", "capsules", "cap", "caps",
    "syrup", "solution", "suspension",
    "cream", "ointment", "gel", "drops",
    "oral", "po",
}

def normalize_query(q: str) -> str:
    q = q.lower().strip()
    q = q.replace("־", "-")  # hebrew dash normalization (optional)
    q = re.sub(r"[^\w\s/.-]", " ", q)  # remove punctuation
    q = re.sub(r"\s+", " ", q).strip()
    return q

def _normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s/.-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _simplify_tokens(q: str) -> List[str]:
    q = _normalize(q)
    toks: List[str] = []
    for t in q.split():
        if t in _STOPWORDS:
            continue
        if t.isdigit():
            continue
        if re.fullmatch(r"\d+(\.\d+)?(mg|mcg|g|ml)", t):
            continue
        if len(t) < 2:
            continue
        toks.append(t)
    return toks

def inventory_check(payload: Dict[str, Any]) -> InventoryCheckOutput:
    """
    Search medication by free-text query and return stock.
    Pass 1: broad LIKE on whole query.
    Pass 2: tokenized fallback stripping strength/form words (e.g., "200 mg tablets").
    """
    inp = InventoryCheckInput.model_validate(payload)
    raw_q = inp.query.strip()
    q = _normalize(raw_q)

    if not q:
        return InventoryCheckOutput(
            ok=False,
            error=ToolError(code="INVALID_QUERY", message="Query must be non-empty."),
            matches=[],
        )

    conn = get_conn()
    try:
        # ---- PASS 1: whole-query LIKE (your current behavior) ----
        like = f"%{q}%"
        rows = conn.execute(
            """
            SELECT m.med_id,
                   m.brand_name,
                   m.generic_name,
                   m.active_ingredients,
                   m.form,
                   m.strength,
                   m.rx_required,
                   i.qty_on_hand
            FROM medications m
            JOIN inventory i ON i.med_id = m.med_id
            WHERE lower(m.brand_name) LIKE ?
               OR lower(m.generic_name) LIKE ?
            ORDER BY (i.qty_on_hand > 0) DESC, m.brand_name ASC
            """,
            (like, like),
        ).fetchall()

        # ---- PASS 2: tokenized fallback ----
        if not rows:
            toks = _simplify_tokens(raw_q)
            if toks:
                # AND across tokens; each token can match brand OR generic
                where = " AND ".join(["(lower(m.brand_name) LIKE ? OR lower(m.generic_name) LIKE ?)"] * len(toks))
                params: List[str] = []
                for t in toks:
                    like_t = f"%{t}%"
                    params.extend([like_t, like_t])

                sql = f"""
                SELECT m.med_id,
                       m.brand_name,
                       m.generic_name,
                       m.active_ingredients,
                       m.form,
                       m.strength,
                       m.rx_required,
                       i.qty_on_hand
                FROM medications m
                JOIN inventory i ON i.med_id = m.med_id
                WHERE {where}
                ORDER BY (i.qty_on_hand > 0) DESC, m.brand_name ASC
                """
                rows = conn.execute(sql, params).fetchall()

        if not rows:
            return InventoryCheckOutput(
                ok=False,
                error=ToolError(code="MED_NOT_FOUND", message="No medication matched the query."),
                matches=[],
            )

        matches: List[StockedMedication] = []
        for r in rows:
            matches.append(
                StockedMedication(
                    med_id=r["med_id"],
                    brand_name=r["brand_name"],
                    generic_name=r["generic_name"],
                    active_ingredients=json.loads(r["active_ingredients"]),
                    form=r["form"],
                    strength=r["strength"],
                    rx_required=bool(r["rx_required"]),
                    qty_on_hand=int(r["qty_on_hand"]),
                )
            )

        return InventoryCheckOutput(ok=True, matches=matches, notes=None)

    except sqlite3.Error as e:
        return InventoryCheckOutput(
            ok=False,
            error=ToolError(code="DB_ERROR", message=str(e)),
            matches=[],
        )

    finally:
        conn.close()




def inventory_find_equivalent(payload: Dict[str, Any]) -> InventoryFindEquivalentOutput:
    """
    Given a med_id, return equivalent options (same active ingredients, and optionally same form/strength).
    Intended for out-of-stock cases.
    """
    inp = InventoryFindEquivalentInput.model_validate(payload)
    conn = get_conn()
    try:
        req = conn.execute(
            """
            SELECT m.med_id,
                   m.brand_name,
                   m.generic_name,
                   m.active_ingredients,
                   m.form,
                   m.strength,
                   m.rx_required,
                   i.qty_on_hand
            FROM medications m
                     JOIN inventory i ON i.med_id = m.med_id
            WHERE m.med_id = ?
            """,
            (inp.med_id,),
        ).fetchone()

        if req is None:
            return InventoryFindEquivalentOutput(
                ok=False,
                error=ToolError(code="MED_NOT_FOUND", message="Requested med_id not found."),
                requested=None,
                equivalents=[],
            )

        requested = StockedMedication(
            med_id=req["med_id"],
            brand_name=req["brand_name"],
            generic_name=req["generic_name"],
            active_ingredients=json.loads(req["active_ingredients"]),
            form=req["form"],
            strength=req["strength"],
            rx_required=bool(req["rx_required"]),
            qty_on_hand=int(req["qty_on_hand"]),
        )

        # Build equivalence query
        clauses = ["m.active_ingredients = ?", "m.med_id != ?"]
        params: List[Any] = [req["active_ingredients"], inp.med_id]

        if inp.require_same_form:
            clauses.append("m.form = ?")
            params.append(req["form"])
        if inp.require_same_strength:
            clauses.append("m.strength = ?")
            params.append(req["strength"])

        where_sql = " AND ".join(clauses)

        rows = conn.execute(
            f"""
                SELECT
                  m.med_id, m.brand_name, m.generic_name, m.active_ingredients,
                  m.form, m.strength, m.rx_required,
                  i.qty_on_hand
                FROM medications m
                JOIN inventory i ON i.med_id = m.med_id
                WHERE {where_sql}
                ORDER BY i.qty_on_hand DESC, m.brand_name ASC
                """,
            tuple(params),
        ).fetchall()

        if not rows:
            return InventoryFindEquivalentOutput(
                ok=False,
                error=ToolError(code="NO_EQUIVALENTS_FOUND", message="No identical-equivalent options found."),
                requested=requested,
                equivalents=[],
            )

        equivalents: List[EquivalentOption] = []
        for r in rows:
            disclosure = EquivalentDisclosure(
                same_active_ingredients=True,
                same_form=(r["form"] == req["form"]),
                same_strength=(r["strength"] == req["strength"]),
                possible_differences=["price", "inactive ingredients", "packaging"],
            )
            equivalents.append(
                EquivalentOption(
                    med_id=r["med_id"],
                    brand_name=r["brand_name"],
                    generic_name=r["generic_name"],
                    active_ingredients=json.loads(r["active_ingredients"]),
                    form=r["form"],
                    strength=r["strength"],
                    rx_required=bool(r["rx_required"]),
                    qty_on_hand=int(r["qty_on_hand"]),
                    disclosure=disclosure,
                )
            )

        return InventoryFindEquivalentOutput(
            ok=True,
            requested=requested,
            equivalents=equivalents,
            notes=None,
        )

    except sqlite3.Error as e:
        return InventoryFindEquivalentOutput(
            ok=False,
            error=ToolError(code="DB_ERROR", message=str(e)),
            requested=None,
            equivalents=[],
        )

    finally:
        conn.close()

def _row_to_stocked_med(row: Any) -> Dict[str, Any]:
    # row columns must match the SELECT below
    return {
        "med_id": row["med_id"],
        "brand_name": row["brand_name"],
        "generic_name": row["generic_name"],
        "active_ingredients": json.loads(row["active_ingredients"]),
        "form": row["form"],
        "strength": row["strength"],
        "rx_required": bool(row["rx_required"]),
        "qty_on_hand": int(row["qty_on_hand"]),
    }

def _search_inventory_tokens(tokens: List[str]) -> List[Dict[str, Any]]:
    if not tokens:
        return []

    where_parts = []
    params: List[str] = []
    for t in tokens:
        where_parts.append("(lower(m.brand_name) LIKE ? OR lower(m.generic_name) LIKE ?)")
        like = f"%{t}%"
        params.extend([like, like])

    where_sql = " AND ".join(where_parts)

    sql = f"""
      SELECT
        m.med_id, m.brand_name, m.generic_name, m.active_ingredients,
        m.form, m.strength, m.rx_required,
        i.qty_on_hand
      FROM medications m
      JOIN inventory i ON i.med_id = m.med_id
      WHERE {where_sql}
      ORDER BY
        -- prefer in-stock first
        (i.qty_on_hand > 0) DESC,
        -- prefer brand name matches slightly (heuristic)
        length(m.brand_name) ASC
      LIMIT 10
    """

    conn = get_conn()
    try:
        conn.row_factory = __import__("sqlite3").Row
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_stocked_med(r) for r in rows]
    finally:
        conn.close()