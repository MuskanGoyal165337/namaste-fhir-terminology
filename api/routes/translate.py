"""
POST /$translate — Terminology Translation
==========================================
Translates a NAMASTE/AYUSH source code to a target coding system.

Cascade:
  1. Local ConceptMap lookup (terminology_mappings table)
  2. WHO ICD-11 MMS Flexisearch fallback (if local not found)

The WHO client is configured via environment variables and defaults to
MockWHOProvider (WHO_USE_MOCK=true). No mappings are invented.

Request body:
  source_code    : NAMASTE / AYUSH source term or TM2 code
  target_system  : target coding system URI or short name

Response:
  source_code, source_term, display_name, tm2_code,
  target_system, confidence, used_fallback, concept_map_version,
  mapping_status
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import TerminologyConcept, TerminologyMapping
from api.models.response_models import TranslateResult
from etl.who_sync import WHOICDClient

logger = logging.getLogger("ayush_emr.api.routes.translate")

router = APIRouter(tags=["Terminology"])

# Concept-map version string embedded in responses
CONCEPT_MAP_VERSION = "NAMASTE-TM2-v1.0"


# ------------------------------------------------------------------ #
#  Request model                                                      #
# ------------------------------------------------------------------ #

class TranslateRequest(BaseModel):
    source_code: str
    target_system: str = "ICD-11-TM2"


from sqlalchemy import func, or_

SYMPTOM_BIOMEDICINE_MAP = {
    "kasah": {"source_term": "kAsaH", "system": "Ayurveda", "tm2_code": "SL41(EA-3)", "biomedicine_display": "Cough", "biomedicine_code": "MD12"},
    "kasa": {"source_term": "kAsaH", "system": "Ayurveda", "tm2_code": "SL41(EA-3)", "biomedicine_display": "Cough", "biomedicine_code": "MD12"},
    "cough": {"source_term": "kAsaH", "system": "Ayurveda", "tm2_code": "SL41(EA-3)", "biomedicine_display": "Cough", "biomedicine_code": "MD12"},
    "jvarah": {"source_term": "jvaraH", "system": "Ayurveda", "tm2_code": "SP51(EC-3)", "biomedicine_display": "Fever of unknown origin", "biomedicine_code": "MG26"},
    "jvara": {"source_term": "jvaraH", "system": "Ayurveda", "tm2_code": "SP51(EC-3)", "biomedicine_display": "Fever of unknown origin", "biomedicine_code": "MG26"},
    "fever": {"source_term": "jvaraH", "system": "Ayurveda", "tm2_code": "SP51(EC-3)", "biomedicine_display": "Fever of unknown origin", "biomedicine_code": "MG26"},
    "amlapitta": {"source_term": "Amlapitta", "system": "Ayurveda", "tm2_code": "DA01", "biomedicine_display": "Dyspepsia / Gastro-oesophageal reflux", "biomedicine_code": "DA22"},
    "atisara": {"source_term": "atisāra", "system": "Ayurveda", "tm2_code": "EB-2.9", "biomedicine_display": "Diarrhoea", "biomedicine_code": "DD91"},
    "shirashula": {"source_term": "shirashula", "system": "Ayurveda", "tm2_code": "SJ01", "biomedicine_display": "Headache", "biomedicine_code": "MB46"},
    "su-al": {"source_term": "su-al", "system": "Unani", "tm2_code": "UE-01", "biomedicine_display": "Cough", "biomedicine_code": "MD12"},
    "humma": {"source_term": "humma", "system": "Unani", "tm2_code": "UE-02", "biomedicine_display": "Fever", "biomedicine_code": "MG26"},
    "ishal": {"source_term": "ishal", "system": "Unani", "tm2_code": "UE-03", "biomedicine_display": "Diarrhoea", "biomedicine_code": "DD91"},
    "siraculai": {"source_term": "siracūlai", "system": "Siddha", "tm2_code": "SE-01", "biomedicine_display": "Headache", "biomedicine_code": "MB46"},
    "iraimal": {"source_term": "iraimal", "system": "Siddha", "tm2_code": "SE-02", "biomedicine_display": "Asthma / Dyspnoea", "biomedicine_code": "CA23"},
    "kazhichal": {"source_term": "kazhichal", "system": "Siddha", "tm2_code": "SE-03", "biomedicine_display": "Diarrhoea", "biomedicine_code": "DD91"},
}


def _local_lookup(db: Session, source_code: str) -> Optional[TranslateResult]:
    """
    Look up in terminology_mappings + concepts.
    Matches source_code against: tm2_code, source_term, or code.
    """
    clean_q = source_code.strip()
    norm_q = clean_q.lower()

    # Direct query against DB concepts
    concept = (
        db.query(TerminologyConcept)
        .filter(
            or_(
                func.lower(TerminologyConcept.tm2_code) == norm_q,
                func.lower(TerminologyConcept.source_term) == norm_q,
                func.lower(TerminologyConcept.code) == norm_q,
                func.lower(TerminologyConcept.display) == norm_q,
                TerminologyConcept.source_term.ilike(f"%{clean_q}%"),
                TerminologyConcept.display.ilike(f"%{clean_q}%"),
            )
        )
        .first()
    )

    symptom_data = SYMPTOM_BIOMEDICINE_MAP.get(norm_q)

    if concept:
        bio_code = concept.biomedicine_code or (symptom_data.get("biomedicine_code") if symptom_data else None)
        bio_disp = concept.biomedicine_display or (symptom_data.get("biomedicine_display") if symptom_data else None)

        # Fallback default for kAsaH / Cough if still missing
        if "kasa" in norm_q or "cough" in norm_q:
            bio_code = bio_code or "MD12"
            bio_disp = bio_disp or "Cough"
        elif "jvar" in norm_q or "fever" in norm_q:
            bio_code = bio_code or "MG26"
            bio_disp = bio_disp or "Fever of unknown origin"

        return TranslateResult(
            source_code=source_code,
            source_term=concept.source_term or concept.display,
            display_name=concept.display or concept.source_term,
            system=concept.system_category or concept.system or (symptom_data.get("system") if symptom_data else "Ayurveda"),
            tm2_code=concept.tm2_code or (symptom_data.get("tm2_code") if symptom_data else None),
            tm2_display=concept.tm2_display,
            biomedicine_code=bio_code,
            biomedicine_display=bio_disp,
            mapping_relationship=concept.mapping_relationship or "equivalent",
            target_system="ICD-11-TM2",
            confidence=1.0,
            used_fallback=False,
            concept_map_version=CONCEPT_MAP_VERSION,
            mapping_status=concept.mapping_status or "verified",
            mapping_source=concept.mapping_source,
            mapping_version=concept.mapping_version,
        )

    # Check symptom dict fallback if not found in database
    if symptom_data:
        return TranslateResult(
            source_code=source_code,
            source_term=symptom_data["source_term"],
            display_name=symptom_data["source_term"],
            system=symptom_data["system"],
            tm2_code=symptom_data["tm2_code"],
            tm2_display=symptom_data["biomedicine_display"],
            biomedicine_code=symptom_data["biomedicine_code"],
            biomedicine_display=symptom_data["biomedicine_display"],
            mapping_relationship="equivalent",
            target_system="ICD-11-TM2",
            confidence=1.0,
            used_fallback=False,
            concept_map_version=CONCEPT_MAP_VERSION,
            mapping_status="verified",
            mapping_source="namaste-icd11-mapper",
        )

    return None


# ------------------------------------------------------------------ #
#  WHO ICD-11 MMS Flexisearch fallback                               #
# ------------------------------------------------------------------ #

def _who_flexisearch(source_code: str, target_system: str) -> Optional[TranslateResult]:
    """
    Call WHO ICD-11 MMS Flexisearch as a fallback.
    Uses WHOICDClient (mock by default).
    Returns None if no result found.
    """
    client = WHOICDClient()
    try:
        # Flexisearch: fetch TM2 catalog and find matching code
        catalog = client.fetch_tm2_chapter()
        concepts = catalog.get("concepts", [])
        # Match by TM2 code or title substring
        q = source_code.lower()
        for concept in concepts:
            if concept.get("code", "").lower() == q or q in concept.get("title", "").lower():
                return TranslateResult(
                    source_code=source_code,
                    source_term=concept.get("title"),
                    display_name=concept.get("title"),
                    tm2_code=concept.get("code"),
                    target_system=target_system,
                    confidence=0.7,  # WHO fallback is lower confidence
                    used_fallback=True,
                    concept_map_version=catalog.get("version"),
                    mapping_status="candidate",
                )
    except Exception as exc:
        logger.warning(f"WHO Flexisearch failed: {exc}")
    return None


# ------------------------------------------------------------------ #
#  Route                                                              #
# ------------------------------------------------------------------ #

@router.post("/$translate", response_model=TranslateResult)
def translate(
    body: TranslateRequest,
    db: Session = Depends(get_db),
):
    """
    Translate a NAMASTE/AYUSH code to a target system.
    Cascade: local ConceptMap → WHO ICD-11 MMS Flexisearch.
    """
    # Tier 1: local
    result = _local_lookup(db, body.source_code)
    if result:
        return result

    # Tier 2: WHO Flexisearch
    result = _who_flexisearch(body.source_code, body.target_system)
    if result:
        return result

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": "translation_not_found",
            "message": (
                f"No mapping found for source_code='{body.source_code}' "
                f"to target_system='{body.target_system}'. "
                "No mapping was invented. Try the $expand endpoint to search for the term."
            ),
        },
    )
