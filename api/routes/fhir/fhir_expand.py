"""
fhir/fhir_expand.py
====================
GET /fhir/$expand — FHIR-compatible ValueSet expansion / autocomplete

Supports:
  - exact code match          (case-insensitive)
  - substring match on term   (case-insensitive)
  - substring match on English display
  - system/category filter
  - limit

Response is a FHIR ValueSet $expand resource with a contains[] array.
Each entry includes all terminology metadata available in the DB.

This endpoint is separate from /$expand (Layer 4 cascade) to keep the
FHIR surface clean and to avoid coupling the existing AI-assisted search.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import TerminologyConcept

logger = logging.getLogger("ayush_emr.api.fhir.expand")

router = APIRouter(prefix="/fhir", tags=["FHIR Terminology"])

NAMASTE_SYSTEM_URI = "http://namaste.ayush.gov.in"
TM2_SYSTEM_URI = "http://id.who.int/icd/release/11/mms"
CS_VERSION = "2024-v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_contains(row: TerminologyConcept) -> Dict[str, Any]:
    """Convert a DB concept row to a FHIR ValueSet contains entry."""
    entry: Dict[str, Any] = {
        "system": NAMASTE_SYSTEM_URI,
        "code": row.source_term or row.code or "",
        "display": row.display or "",
        "version": row.source_version or CS_VERSION,
    }
    # Populate optional extension-style properties
    ext: List[Dict[str, Any]] = []
    if row.system_category:
        ext.append({"code": "system_category", "valueString": row.system_category})
    if row.tm2_code:
        ext.append({"code": "tm2_code", "valueString": row.tm2_code})
        ext.append({
            "code": "tm2_display",
            "valueString": row.tm2_display or f"ICD-11 TM2 Code {row.tm2_code}",
        })
    # biomedicine_code: always null for current dataset — explicitly represented
    ext.append({
        "code": "biomedicine_code",
        "valueString": row.biomedicine_code or "__unmapped__",
    })
    ext.append({
        "code": "mapping_status",
        "valueString": row.mapping_status or "unknown",
    })
    if ext:
        entry["extension"] = ext
    return entry


@router.get("/$expand", summary="FHIR ValueSet $expand / autocomplete")
def fhir_expand(
    q: str = Query(..., min_length=1, description="Search term (partial or full)"),
    system: Optional[str] = Query(None, description="Filter by AYUSH system category"),
    exact: bool = Query(False, description="If true, only exact matches are returned"),
    limit: int = Query(20, ge=1, le=100, description="Maximum entries to return"),
    db: Session = Depends(get_db),
):
    """
    FHIR R4-compatible ValueSet $expand operation.

    Performs case-insensitive substring search across source_term (original
    transliterated term) and display (English translation).  Use exact=true
    for strict code-level lookup.

    Returned resource is a FHIR ValueSet with an expansion.contains[] array.
    Each entry includes tm2_code, biomedicine_code (null for current data),
    and mapping_status.
    """
    # Exclude ICD-11-TM2 rows — this expands the NAMASTE ValueSet
    base_query = db.query(TerminologyConcept).filter(
        TerminologyConcept.system != TM2_SYSTEM_URI,
        TerminologyConcept.system_category != "ICD-11-TM2",
    )
    if system:
        base_query = base_query.filter(TerminologyConcept.system_category == system)

    if exact:
        # Case-insensitive exact match on code or source_term
        q_lower = q.lower()
        rows = base_query.filter(
            or_(
                func.lower(TerminologyConcept.source_term) == q_lower,
                func.lower(TerminologyConcept.code) == q_lower,
            )
        ).limit(limit).all()
    else:
        # Substring match on source_term or display (case-insensitive)
        q_like = f"%{q.lower()}%"
        rows = base_query.filter(
            or_(
                func.lower(TerminologyConcept.source_term).like(q_like),
                func.lower(TerminologyConcept.display).like(q_like),
                func.lower(TerminologyConcept.english).like(q_like),
            )
        ).limit(limit).all()

    contains = [_row_to_contains(r) for r in rows]

    return {
        "resourceType": "ValueSet",
        "id": "valueset-namaste-ayush-expansion",
        "url": f"{NAMASTE_SYSTEM_URI}/fhir/ValueSet/namaste-ayush",
        "version": CS_VERSION,
        "status": "active",
        "expansion": {
            "timestamp": _utc_now(),
            "total": len(contains),
            "parameter": [
                {"name": "q", "valueString": q},
                {"name": "exact", "valueBoolean": exact},
                {"name": "limit", "valueInteger": limit},
                *([{"name": "system", "valueString": system}] if system else []),
            ],
            "contains": contains,
        },
    }
