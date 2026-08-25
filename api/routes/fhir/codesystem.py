"""
fhir/codesystem.py
==================
FHIR R4 CodeSystem read endpoints.

Endpoints
---------
GET /fhir/CodeSystem                        — list available CodeSystems
GET /fhir/CodeSystem/namaste-ayush         — NAMASTE AYUSH CodeSystem
GET /fhir/CodeSystem/icd11-tm2             — ICD-11 TM2 CodeSystem (fragment)

All concepts are built from the live database; no codes are invented.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import TerminologyConcept

logger = logging.getLogger("ayush_emr.api.fhir.codesystem")

router = APIRouter(prefix="/fhir/CodeSystem", tags=["FHIR Terminology"])

# ── System URIs ─────────────────────────────────────────────────────────────
NAMASTE_SYSTEM_URI = "http://namaste.ayush.gov.in"
TM2_SYSTEM_URI = "http://id.who.int/icd/release/11/mms"
CS_VERSION = "2024-v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_namaste_codesystem(db: Session, system_filter: Optional[str] = None) -> Dict[str, Any]:
    """
    Build a FHIR R4 CodeSystem from live TerminologyConcept rows.
    Only includes rows that belong to NAMASTE/AYUSH systems (not ICD-11-TM2 rows).
    """
    query = db.query(TerminologyConcept).filter(
        TerminologyConcept.system != TM2_SYSTEM_URI,
        TerminologyConcept.system_category != "ICD-11-TM2",
    )
    if system_filter:
        query = query.filter(TerminologyConcept.system_category == system_filter)

    rows = query.order_by(TerminologyConcept.source_term).all()

    concepts: List[Dict[str, Any]] = []
    for row in rows:
        # Use source_term as the code when no explicit code column is set
        concept_code = row.source_term or row.code
        if not concept_code:
            continue
        concept: Dict[str, Any] = {
            "code": concept_code,
            "display": row.display or concept_code,
        }
        if row.definition:
            concept["definition"] = row.definition
        if row.english and row.english != row.display:
            concept.setdefault("definition", f"English: {row.english}")
        props: List[Dict[str, Any]] = []
        if row.system_category:
            props.append({"code": "system_category", "valueString": row.system_category})
        if row.tm2_code:
            props.append({"code": "tm2_code", "valueString": row.tm2_code})
        if row.mapping_status:
            props.append({"code": "mapping_status", "valueString": row.mapping_status})
        if props:
            concept["property"] = props
        concepts.append(concept)

    return {
        "resourceType": "CodeSystem",
        "id": "codesystem-namaste-ayush",
        "url": NAMASTE_SYSTEM_URI,
        "version": CS_VERSION,
        "name": "NAMASTEAYUSHTerminology",
        "title": "NAMASTE AYUSH Terminology CodeSystem",
        "status": "active",
        "experimental": False,
        "date": _utc_now(),
        "publisher": "Ministry of AYUSH, Government of India",
        "description": (
            "Terminology CodeSystem for traditional AYUSH medicine systems "
            "(Ayurveda, Siddha, Unani, Yoga & Naturopathy) "
            "as defined by the NAMASTE project."
        ),
        "content": "complete",
        "count": len(concepts),
        "property": [
            {"code": "system_category", "type": "string", "description": "AYUSH system category"},
            {"code": "tm2_code", "type": "string", "description": "ICD-11 TM2 code if mapped"},
            {"code": "mapping_status", "type": "string", "description": "Mapping lifecycle status"},
        ],
        "concept": concepts,
    }


def _build_tm2_codesystem(db: Session) -> Dict[str, Any]:
    """
    Build a FHIR R4 CodeSystem fragment for ICD-11 TM2 codes that appear in
    this system's mapping data.  Only codes present in the database are included.
    """
    rows = (
        db.query(TerminologyConcept)
        .filter(
            TerminologyConcept.system == TM2_SYSTEM_URI,
            TerminologyConcept.code.isnot(None),
        )
        .order_by(TerminologyConcept.code)
        .all()
    )

    concepts: List[Dict[str, Any]] = []
    seen: set = set()
    for row in rows:
        if row.code in seen:
            continue
        seen.add(row.code)
        c: Dict[str, Any] = {
            "code": row.code,
            "display": row.tm2_display or row.display or f"ICD-11 TM2 Code {row.code}",
        }
        if row.definition:
            c["definition"] = row.definition
        concepts.append(c)

    return {
        "resourceType": "CodeSystem",
        "id": "codesystem-icd11-tm2",
        "url": TM2_SYSTEM_URI,
        "version": CS_VERSION,
        "name": "ICD11TM2Terminology",
        "title": "WHO ICD-11 Traditional Medicine Module 2 CodeSystem (Fragment)",
        "status": "active",
        "experimental": False,
        "date": _utc_now(),
        "publisher": "World Health Organization (WHO)",
        "description": (
            "Fragment CodeSystem containing only the ICD-11 TM2 codes that are "
            "present in the local mapping dataset.  This is NOT the complete "
            "WHO ICD-11 TM2 CodeSystem."
        ),
        "content": "fragment",
        "count": len(concepts),
        "concept": concepts,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", summary="List available FHIR CodeSystems")
def list_codesystems():
    """Return a FHIR Bundle listing available CodeSystem resources."""
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 2,
        "entry": [
            {
                "fullUrl": f"{NAMASTE_SYSTEM_URI}/fhir/CodeSystem/namaste-ayush",
                "resource": {
                    "resourceType": "CodeSystem",
                    "id": "codesystem-namaste-ayush",
                    "url": NAMASTE_SYSTEM_URI,
                    "name": "NAMASTEAYUSHTerminology",
                    "title": "NAMASTE AYUSH Terminology CodeSystem",
                    "status": "active",
                    "version": CS_VERSION,
                    "content": "complete",
                },
            },
            {
                "fullUrl": f"{NAMASTE_SYSTEM_URI}/fhir/CodeSystem/icd11-tm2",
                "resource": {
                    "resourceType": "CodeSystem",
                    "id": "codesystem-icd11-tm2",
                    "url": TM2_SYSTEM_URI,
                    "name": "ICD11TM2Terminology",
                    "title": "WHO ICD-11 Traditional Medicine Module 2 CodeSystem (Fragment)",
                    "status": "active",
                    "version": CS_VERSION,
                    "content": "fragment",
                },
            },
        ],
    }


@router.get("/namaste-ayush", summary="NAMASTE AYUSH CodeSystem")
def get_namaste_codesystem(
    system: Optional[str] = Query(None, description="Filter by AYUSH system category"),
    db: Session = Depends(get_db),
):
    """
    Returns the FHIR R4 CodeSystem resource for NAMASTE AYUSH terminology,
    populated from the live database.  All codes are sourced from actual
    ingested data — none are invented.
    """
    return _build_namaste_codesystem(db, system_filter=system)


@router.get("/icd11-tm2", summary="ICD-11 TM2 CodeSystem fragment")
def get_tm2_codesystem(db: Session = Depends(get_db)):
    """
    Returns a FHIR R4 CodeSystem fragment for ICD-11 TM2 codes referenced
    in the local mapping dataset.  This is NOT the authoritative complete
    WHO ICD-11 TM2 CodeSystem.
    """
    return _build_tm2_codesystem(db)
