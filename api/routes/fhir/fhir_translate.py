"""
fhir/fhir_translate.py
=======================
POST /fhir/$translate — FHIR R4-compatible $translate operation

Supported translation chains:
  NAMASTE → ICD-11-TM2        (local mapping table)
  ICD-11-TM2 → NAMASTE        (reverse lookup)
  TM2 → ICD-11 Biomedicine    (only if DB has an authoritative biomedicine_code)
  NAMASTE → ICD-11 Biomedicine (via NAMASTE→TM2→Biomedicine chain, only if data exists)

Rules:
  - No codes are inferred or fabricated.
  - If no mapping exists, result.result = false and match = unmatched.
  - biomedicine_code is null for current data and always will be unless an
    authoritative external source populates it.
  - Validation distinguishes: valid, unmapped, invalid, unsupported.

Request:
  code        : source code (source_term or tm2_code or code column)
  system      : source system URI (optional; used when code is ambiguous)
  target      : target system URI

Response: FHIR Parameters resource (result, match[])
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import TerminologyConcept, TerminologyMapping

logger = logging.getLogger("ayush_emr.api.fhir.translate")

router = APIRouter(prefix="/fhir", tags=["FHIR Terminology"])

NAMASTE_SYSTEM_URI = "http://namaste.ayush.gov.in"
TM2_SYSTEM_URI = "http://id.who.int/icd/release/11/mms"
BIOMEDICINE_SYSTEM_URI = "http://id.who.int/icd/release/11/mms/biomedical"

SUPPORTED_TARGETS = {TM2_SYSTEM_URI, NAMASTE_SYSTEM_URI, BIOMEDICINE_SYSTEM_URI}
SUPPORTED_SOURCES = {NAMASTE_SYSTEM_URI, TM2_SYSTEM_URI}

CM_VERSION = "2024-v1"

FHIR_EQUIVALENCE = {
    "exact":          "equal",
    "equivalent":     "equivalent",
    "broader":        "wider",
    "narrower":       "narrower",
    "related":        "relatedto",
    "not-mapped":     "unmatched",
    "not-applicable": "unmatched",
}


def _db_rel_to_fhir(rel: Optional[str]) -> str:
    return FHIR_EQUIVALENCE.get(rel or "", "relatedto")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TranslationValidationStatus:
    VALID = "valid"
    UNMAPPED = "unmapped"
    INVALID_CODE = "invalid"
    UNSUPPORTED = "unsupported"
    MISSING_TARGET = "missing_target"


def _validate_source(db: Session, code: str, system: Optional[str]) -> tuple[
    Optional[TerminologyConcept], str
]:
    """
    Look up source concept.  Returns (concept, validation_status).
    validation_status is one of TranslationValidationStatus constants.
    """
    if system and system not in SUPPORTED_SOURCES:
        return None, TranslationValidationStatus.UNSUPPORTED

    # Build candidate filter: tm2_code OR source_term OR code column
    concept = (
        db.query(TerminologyConcept)
        .filter(
            (TerminologyConcept.source_term == code)
            | (TerminologyConcept.code == code)
            | (TerminologyConcept.tm2_code == code)
        )
        .first()
    )
    if not concept:
        return None, TranslationValidationStatus.INVALID_CODE
    return concept, TranslationValidationStatus.VALID


def _validate_target_system(target: str) -> str:
    if target not in SUPPORTED_TARGETS:
        return TranslationValidationStatus.UNSUPPORTED
    return TranslationValidationStatus.VALID


# ---------------------------------------------------------------------------
# Request / Response Pydantic models
# ---------------------------------------------------------------------------

class FHIRTranslateRequest(BaseModel):
    code: str
    system: Optional[str] = None          # source system URI
    target: str = TM2_SYSTEM_URI          # target system URI
    reverse: bool = False                 # if true, look up reverse mapping

    @field_validator("target")
    @classmethod
    def _check_target(cls, v: str) -> str:
        if v not in SUPPORTED_TARGETS:
            raise ValueError(
                f"Unsupported target system '{v}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_TARGETS))}"
            )
        return v


# ---------------------------------------------------------------------------
# Translation helpers
# ---------------------------------------------------------------------------

def _namaste_to_tm2(
    db: Session, concept: TerminologyConcept
) -> Optional[Dict[str, Any]]:
    """Return FHIR match part for NAMASTE→TM2."""
    mapping = (
        db.query(TerminologyMapping)
        .filter(TerminologyMapping.source_concept_id == concept.id)
        .first()
    )
    if not mapping:
        # Also check if concept has a tm2_code directly (from CSV ingestion)
        if concept.tm2_code:
            return {
                "source": NAMASTE_SYSTEM_URI,
                "target_system": TM2_SYSTEM_URI,
                "target_code": concept.tm2_code,
                "target_display": concept.tm2_display or f"ICD-11 TM2 Code {concept.tm2_code}",
                "equivalence": _db_rel_to_fhir(concept.mapping_relationship),
                "mapping_status": concept.mapping_status or "verified",
                "mapping_source": concept.mapping_source,
                "used_reverse": False,
            }
        return None

    target: Optional[TerminologyConcept] = (
        db.query(TerminologyConcept)
        .filter(TerminologyConcept.id == mapping.target_concept_id)
        .first()
    )
    return {
        "source": NAMASTE_SYSTEM_URI,
        "target_system": TM2_SYSTEM_URI,
        "target_code": target.code if target else concept.tm2_code,
        "target_display": (
            (target.tm2_display or target.display) if target
            else f"ICD-11 TM2 Code {concept.tm2_code}"
        ),
        "equivalence": _db_rel_to_fhir(mapping.relationship_type),
        "mapping_status": mapping.mapping_status,
        "mapping_source": mapping.mapping_source,
        "used_reverse": False,
    }


def _tm2_to_namaste(db: Session, concept: TerminologyConcept) -> Optional[Dict[str, Any]]:
    """Return FHIR match part for TM2→NAMASTE (reverse)."""
    # Check if the concept's own tm2_code matches to find the NAMASTE source
    # Pattern: concept is a TM2-system concept; look for TerminologyMapping.target = concept
    mapping = (
        db.query(TerminologyMapping)
        .filter(TerminologyMapping.target_concept_id == concept.id)
        .first()
    )
    if not mapping:
        # Also search NAMASTE concepts that carry this tm2_code
        namaste_concept = (
            db.query(TerminologyConcept)
            .filter(
                TerminologyConcept.tm2_code == (concept.code or concept.tm2_code),
                TerminologyConcept.system_category != "ICD-11-TM2",
            )
            .first()
        )
        if namaste_concept:
            code = namaste_concept.source_term or namaste_concept.code
            return {
                "source": TM2_SYSTEM_URI,
                "target_system": NAMASTE_SYSTEM_URI,
                "target_code": code,
                "target_display": namaste_concept.display,
                "equivalence": _db_rel_to_fhir(namaste_concept.mapping_relationship),
                "mapping_status": namaste_concept.mapping_status or "verified",
                "mapping_source": namaste_concept.mapping_source,
                "used_reverse": True,
            }
        return None

    source_concept: Optional[TerminologyConcept] = (
        db.query(TerminologyConcept)
        .filter(TerminologyConcept.id == mapping.source_concept_id)
        .first()
    )
    if not source_concept:
        return None
    namaste_code = source_concept.source_term or source_concept.code
    return {
        "source": TM2_SYSTEM_URI,
        "target_system": NAMASTE_SYSTEM_URI,
        "target_code": namaste_code,
        "target_display": source_concept.display,
        "equivalence": _db_rel_to_fhir(mapping.relationship_type),
        "mapping_status": mapping.mapping_status,
        "mapping_source": mapping.mapping_source,
        "used_reverse": True,
    }


def _to_biomedicine(concept: TerminologyConcept) -> Optional[Dict[str, Any]]:
    """
    Return FHIR match part for →ICD-11 Biomedicine.
    Only if biomedicine_code is explicitly populated (not null).
    NEVER fabricates or infers a biomedicine code.
    """
    if not concept.biomedicine_code:
        return None
    return {
        "source": concept.system,
        "target_system": BIOMEDICINE_SYSTEM_URI,
        "target_code": concept.biomedicine_code,
        "target_display": concept.biomedicine_display or concept.biomedicine_code,
        "equivalence": "equivalent",
        "mapping_status": "verified",
        "mapping_source": concept.mapping_source,
        "used_reverse": False,
    }


def _build_fhir_parameters(
    request_code: str,
    request_target: str,
    matched: bool,
    match_data: Optional[Dict[str, Any]],
    validation_status: str,
    validation_message: str,
) -> Dict[str, Any]:
    """Build a FHIR R4 Parameters resource for a $translate response."""
    parts: List[Dict[str, Any]] = [
        {"name": "result", "valueBoolean": matched},
        {"name": "validation_status", "valueString": validation_status},
    ]
    if not matched:
        parts.append({"name": "message", "valueString": validation_message})

    if matched and match_data:
        match_parts: List[Dict[str, Any]] = [
            {
                "name": "equivalence",
                "valueCoding": {
                    "system": "http://hl7.org/fhir/concept-map-equivalence",
                    "code": match_data["equivalence"],
                },
            },
            {
                "name": "concept",
                "valueCoding": {
                    "system": match_data["target_system"],
                    "code": match_data["target_code"],
                    "display": match_data.get("target_display", ""),
                    "version": CM_VERSION,
                },
            },
            {
                "name": "source",
                "valueUri": f"{NAMASTE_SYSTEM_URI}/fhir/ConceptMap/namaste-to-icd11-tm2",
            },
        ]
        if match_data.get("mapping_status"):
            match_parts.append({
                "name": "mapping_status",
                "valueString": match_data["mapping_status"],
            })
        if match_data.get("mapping_source"):
            match_parts.append({
                "name": "mapping_source",
                "valueString": match_data["mapping_source"],
            })
        if match_data.get("used_reverse"):
            match_parts.append({"name": "used_reverse", "valueBoolean": True})
        # Biomedicine note
        parts.append({
            "name": "match",
            "part": match_parts,
        })
        # Always include biomedicine note (important for audit/transparency)
        parts.append({
            "name": "biomedicine_note",
            "valueString": (
                "biomedicine_code is null for the current dataset. "
                "ICD-11 Biomedicine codes are never inferred or fabricated."
            ),
        })

    return {
        "resourceType": "Parameters",
        "parameter": parts,
    }


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("/$translate", summary="FHIR $translate terminology operation")
def fhir_translate(
    body: FHIRTranslateRequest,
    db: Session = Depends(get_db),
):
    """
    FHIR R4 $translate operation.

    Supports:
      NAMASTE → ICD-11-TM2
      ICD-11-TM2 → NAMASTE
      * → ICD-11 Biomedicine (only when biomedicine_code is populated in DB)
      NAMASTE → ICD-11 Biomedicine via chain (only when data permits)

    Returns a FHIR Parameters resource.
    result=false with validation_status if no mapping found.
    """
    target = body.target

    # ── 1. Validate target system ─────────────────────────────────────────
    ts_status = _validate_target_system(target)
    if ts_status != TranslationValidationStatus.VALID:
        return _build_fhir_parameters(
            request_code=body.code,
            request_target=target,
            matched=False,
            match_data=None,
            validation_status=TranslationValidationStatus.UNSUPPORTED,
            validation_message=(
                f"Target system '{target}' is not supported. "
                f"Supported: {', '.join(sorted(SUPPORTED_TARGETS))}"
            ),
        )

    # ── 2. Look up source concept ─────────────────────────────────────────
    concept, src_status = _validate_source(db, body.code, body.system)

    if src_status == TranslationValidationStatus.UNSUPPORTED:
        return _build_fhir_parameters(
            request_code=body.code,
            request_target=target,
            matched=False,
            match_data=None,
            validation_status=TranslationValidationStatus.UNSUPPORTED,
            validation_message=(
                f"Source system '{body.system}' is not supported. "
                f"Supported: {', '.join(sorted(SUPPORTED_SOURCES))}"
            ),
        )

    if src_status == TranslationValidationStatus.INVALID_CODE or concept is None:
        return _build_fhir_parameters(
            request_code=body.code,
            request_target=target,
            matched=False,
            match_data=None,
            validation_status=TranslationValidationStatus.INVALID_CODE,
            validation_message=(
                f"Code '{body.code}' was not found in the local terminology database. "
                "Use /fhir/$expand to search for valid terms."
            ),
        )

    # ── 3. Perform translation ────────────────────────────────────────────
    match_data: Optional[Dict[str, Any]] = None

    if target == BIOMEDICINE_SYSTEM_URI:
        # Direct biomedicine lookup
        match_data = _to_biomedicine(concept)
        if match_data is None and concept.tm2_code:
            # Try via TM2 concept (chain)
            tm2_concept = (
                db.query(TerminologyConcept)
                .filter(
                    TerminologyConcept.code == concept.tm2_code,
                    TerminologyConcept.system == TM2_SYSTEM_URI,
                )
                .first()
            )
            if tm2_concept:
                match_data = _to_biomedicine(tm2_concept)

    elif target == TM2_SYSTEM_URI:
        # NAMASTE → TM2 (or TM2 → TM2 identity)
        if concept.system_category == "ICD-11-TM2" or concept.system == TM2_SYSTEM_URI:
            # Source is already a TM2 concept — identity
            match_data = {
                "source": TM2_SYSTEM_URI,
                "target_system": TM2_SYSTEM_URI,
                "target_code": concept.code or concept.tm2_code,
                "target_display": concept.tm2_display or concept.display,
                "equivalence": "equal",
                "mapping_status": "verified",
                "mapping_source": concept.mapping_source,
                "used_reverse": False,
            }
        else:
            match_data = _namaste_to_tm2(db, concept)

    elif target == NAMASTE_SYSTEM_URI:
        # TM2 → NAMASTE (reverse)
        if concept.system_category != "ICD-11-TM2" and concept.system != TM2_SYSTEM_URI:
            # Source is already NAMASTE — identity
            match_data = {
                "source": NAMASTE_SYSTEM_URI,
                "target_system": NAMASTE_SYSTEM_URI,
                "target_code": concept.source_term or concept.code,
                "target_display": concept.display,
                "equivalence": "equal",
                "mapping_status": "verified",
                "mapping_source": concept.mapping_source,
                "used_reverse": False,
            }
        else:
            match_data = _tm2_to_namaste(db, concept)

    # ── 4. Build response ─────────────────────────────────────────────────
    if match_data:
        return _build_fhir_parameters(
            request_code=body.code,
            request_target=target,
            matched=True,
            match_data=match_data,
            validation_status=TranslationValidationStatus.VALID,
            validation_message="",
        )

    return _build_fhir_parameters(
        request_code=body.code,
        request_target=target,
        matched=False,
        match_data=None,
        validation_status=TranslationValidationStatus.UNMAPPED,
        validation_message=(
            f"No mapping found from '{body.code}' to target system '{target}'. "
            "No mapping was invented. "
            "This concept may not have an authoritative mapping in the local dataset."
        ),
    )
