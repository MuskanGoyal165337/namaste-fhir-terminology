"""
fhir/conceptmap.py
==================
FHIR R4 ConceptMap read endpoints.

Endpoints
---------
GET /fhir/ConceptMap                           — list available ConceptMaps
GET /fhir/ConceptMap/namaste-to-icd11-tm2      — NAMASTE → ICD-11-TM2 map
GET /fhir/ConceptMap/icd11-tm2-to-namaste      — ICD-11-TM2 → NAMASTE (reverse)

Only mappings backed by actual database rows are included.
Unmapped concepts appear in an unmatched group.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import TerminologyConcept, TerminologyMapping

logger = logging.getLogger("ayush_emr.api.fhir.conceptmap")

router = APIRouter(prefix="/fhir/ConceptMap", tags=["FHIR Terminology"])

NAMASTE_SYSTEM_URI = "http://namaste.ayush.gov.in"
TM2_SYSTEM_URI     = "http://id.who.int/icd/release/11/mms"
CM_VERSION         = "2024-v1"
CM_BASE_URI        = "http://namaste.ayush.gov.in/fhir/ConceptMap"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# FHIR ConceptMap equivalence mapping
# ---------------------------------------------------------------------------

_FHIR_EQUIVALENCE = {
    "exact":          "equal",
    "equivalent":     "equivalent",
    "broader":        "wider",
    "narrower":       "narrower",
    "related":        "relatedto",
    "not-mapped":     "unmatched",
    "not-applicable": "unmatched",
}


def _db_rel_to_fhir(rel: Optional[str]) -> str:
    """Convert MappingRelationship to FHIR R4 ConceptMap equivalence code."""
    return _FHIR_EQUIVALENCE.get(rel or "", "relatedto")


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _build_namaste_to_tm2_conceptmap(db: Session) -> Dict[str, Any]:
    """
    Build a FHIR R4 ConceptMap from TerminologyMapping rows.
    Source: NAMASTE, Target: ICD-11 TM2.
    Unmapped NAMASTE concepts appear in an unmatched group.
    """
    # Load all NAMASTE concepts (not ICD-11-TM2 target rows)
    namaste_rows = (
        db.query(TerminologyConcept)
        .filter(
            TerminologyConcept.system != TM2_SYSTEM_URI,
            TerminologyConcept.system_category != "ICD-11-TM2",
        )
        .all()
    )

    # Build a quick lookup: concept.id → mapping rows
    concept_ids = [r.id for r in namaste_rows]
    mappings = (
        db.query(TerminologyMapping)
        .filter(TerminologyMapping.source_concept_id.in_(concept_ids))
        .all()
    ) if concept_ids else []

    tm2_concept_map: Dict[str, TerminologyConcept] = {}
    for m in mappings:
        tm2_concept_map[m.source_concept_id] = m

    # Split into mapped vs unmapped
    mapped_elements: List[Dict[str, Any]] = []
    unmapped_elements: List[Dict[str, Any]] = []

    for row in namaste_rows:
        code = row.source_term or row.code
        if not code:
            continue
        mapping = tm2_concept_map.get(row.id)
        if mapping:
            # Fetch target TM2 concept for display
            target: Optional[TerminologyConcept] = (
                db.query(TerminologyConcept)
                .filter(TerminologyConcept.id == mapping.target_concept_id)
                .first()
            )
            target_code = target.code if target else row.tm2_code
            target_display = (
                (target.tm2_display or target.display) if target
                else (f"ICD-11 TM2 Code {row.tm2_code}" if row.tm2_code else None)
            )
            fhir_equiv = _db_rel_to_fhir(mapping.relationship_type)
            element: Dict[str, Any] = {
                "code": code,
                "display": row.display or code,
                "target": [
                    {
                        "code": str(target_code),
                        "display": target_display or str(target_code),
                        "equivalence": fhir_equiv,
                    }
                ],
            }
            mapped_elements.append(element)
        else:
            # Unmapped — include with unmatched target
            unmapped_elements.append({
                "code": code,
                "display": row.display or code,
                "target": [
                    {
                        "equivalence": "unmatched",
                        "comment": "No TM2 mapping available for this NAMASTE concept",
                    }
                ],
            })

    groups: List[Dict[str, Any]] = []
    if mapped_elements:
        groups.append({
            "source": NAMASTE_SYSTEM_URI,
            "target": TM2_SYSTEM_URI,
            "element": mapped_elements,
        })
    if unmapped_elements:
        groups.append({
            "source": NAMASTE_SYSTEM_URI,
            "unmapped": {"mode": "fixed", "code": "unmatched", "display": "No mapping available"},
            "element": unmapped_elements,
        })

    return {
        "resourceType": "ConceptMap",
        "id": "conceptmap-namaste-to-icd11-tm2",
        "url": f"{CM_BASE_URI}/namaste-to-icd11-tm2",
        "version": CM_VERSION,
        "name": "NAMASTEToICD11TM2Map",
        "title": "NAMASTE AYUSH Terminology to WHO ICD-11-TM2 ConceptMap",
        "status": "active",
        "experimental": False,
        "date": _utc_now(),
        "publisher": "Ministry of AYUSH, Government of India",
        "description": (
            "Maps NAMASTE AYUSH terminology concepts to WHO ICD-11 Traditional "
            "Medicine Module 2 (TM2) codes.  Unmapped concepts appear in an "
            "unmatched group.  No codes are fabricated."
        ),
        "sourceUri": NAMASTE_SYSTEM_URI,
        "targetUri": TM2_SYSTEM_URI,
        "group": groups,
    }


def _build_tm2_to_namaste_conceptmap(db: Session) -> Dict[str, Any]:
    """
    Build the reverse FHIR R4 ConceptMap: ICD-11 TM2 → NAMASTE.
    Only includes pairs where a TM2 → NAMASTE TerminologyMapping exists.
    """
    # Find mappings where source is a TM2 concept
    tm2_rows = (
        db.query(TerminologyConcept)
        .filter(
            TerminologyConcept.system == TM2_SYSTEM_URI,
            TerminologyConcept.code.isnot(None),
        )
        .all()
    )
    tm2_ids = [r.id for r in tm2_rows]
    tm2_by_id = {r.id: r for r in tm2_rows}

    # Also check for reverse: NAMASTE concepts whose tm2_code maps to TM2 target
    # We support reading through TerminologyMapping target_concept_id
    reverse_mappings = (
        db.query(TerminologyMapping)
        .filter(TerminologyMapping.target_concept_id.in_(tm2_ids))
        .all()
    ) if tm2_ids else []

    elements: List[Dict[str, Any]] = []
    for mapping in reverse_mappings:
        tm2_concept = tm2_by_id.get(mapping.target_concept_id)
        source_concept: Optional[TerminologyConcept] = (
            db.query(TerminologyConcept)
            .filter(TerminologyConcept.id == mapping.source_concept_id)
            .first()
        )
        if not tm2_concept or not source_concept:
            continue
        namaste_code = source_concept.source_term or source_concept.code
        if not namaste_code:
            continue
        fhir_equiv = _db_rel_to_fhir(mapping.relationship_type)
        elements.append({
            "code": tm2_concept.code,
            "display": tm2_concept.tm2_display or tm2_concept.display or tm2_concept.code,
            "target": [
                {
                    "code": namaste_code,
                    "display": source_concept.display or namaste_code,
                    "equivalence": fhir_equiv,
                }
            ],
        })

    return {
        "resourceType": "ConceptMap",
        "id": "conceptmap-icd11-tm2-to-namaste",
        "url": f"{CM_BASE_URI}/icd11-tm2-to-namaste",
        "version": CM_VERSION,
        "name": "ICD11TM2ToNAMASTEMap",
        "title": "WHO ICD-11-TM2 to NAMASTE AYUSH Terminology ConceptMap (Reverse)",
        "status": "active",
        "experimental": False,
        "date": _utc_now(),
        "publisher": "Ministry of AYUSH, Government of India",
        "description": (
            "Reverse ConceptMap: WHO ICD-11 TM2 to NAMASTE AYUSH.  "
            "Only includes pairs with an authoritative reverse mapping in the local dataset."
        ),
        "sourceUri": TM2_SYSTEM_URI,
        "targetUri": NAMASTE_SYSTEM_URI,
        "group": [
            {
                "source": TM2_SYSTEM_URI,
                "target": NAMASTE_SYSTEM_URI,
                "element": elements,
            }
        ] if elements else [],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", summary="List available FHIR ConceptMaps")
def list_conceptmaps():
    """Return a FHIR Bundle listing available ConceptMap resources."""
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 2,
        "entry": [
            {
                "fullUrl": f"{CM_BASE_URI}/namaste-to-icd11-tm2",
                "resource": {
                    "resourceType": "ConceptMap",
                    "id": "conceptmap-namaste-to-icd11-tm2",
                    "url": f"{CM_BASE_URI}/namaste-to-icd11-tm2",
                    "name": "NAMASTEToICD11TM2Map",
                    "status": "active",
                    "version": CM_VERSION,
                    "sourceUri": NAMASTE_SYSTEM_URI,
                    "targetUri": TM2_SYSTEM_URI,
                },
            },
            {
                "fullUrl": f"{CM_BASE_URI}/icd11-tm2-to-namaste",
                "resource": {
                    "resourceType": "ConceptMap",
                    "id": "conceptmap-icd11-tm2-to-namaste",
                    "url": f"{CM_BASE_URI}/icd11-tm2-to-namaste",
                    "name": "ICD11TM2ToNAMASTEMap",
                    "status": "active",
                    "version": CM_VERSION,
                    "sourceUri": TM2_SYSTEM_URI,
                    "targetUri": NAMASTE_SYSTEM_URI,
                },
            },
        ],
    }


@router.get("/namaste-to-icd11-tm2", summary="NAMASTE → ICD-11-TM2 ConceptMap")
def get_namaste_to_tm2_map(db: Session = Depends(get_db)):
    """
    Returns the FHIR R4 ConceptMap for NAMASTE → ICD-11-TM2 mappings.
    Unmapped NAMASTE concepts appear in an 'unmatched' group.
    """
    return _build_namaste_to_tm2_conceptmap(db)


@router.get("/icd11-tm2-to-namaste", summary="ICD-11-TM2 → NAMASTE ConceptMap (reverse)")
def get_tm2_to_namaste_map(db: Session = Depends(get_db)):
    """
    Returns the reverse FHIR R4 ConceptMap: ICD-11-TM2 → NAMASTE.
    Only includes pairs with an authoritative mapping in the local dataset.
    """
    return _build_tm2_to_namaste_conceptmap(db)
