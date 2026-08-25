"""
fhir/problem_list.py
=====================
Problem-list workflow service.

Implements the full clinician double-coding workflow:
  1. Look up traditional diagnosis in terminology DB
  2. Resolve TM2 mapping from DB (authoritative)
  3. Resolve Biomedicine mapping from DB (authoritative; null if not available)
  4. Build a FHIR Condition via ConditionBuilder
  5. Build a FHIR Bundle via build_double_coding_bundle
  6. Persist to DB (FHIRBundle row + ClinicalCondition row)

AI NEVER decides the final codes — all coding is deterministic & DB-driven.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from db.models import TerminologyConcept, FHIRBundle as FHIRBundleModel, ClinicalCondition
from fhir.condition import (
    ConditionBuilder,
    TraditionalDiagnosis,
    EncounterContext,
)
from fhir.bundle import build_double_coding_bundle
from fhir.validation import validate_bundle, BundleValidationResult
from api.models.fhir_models import Condition

logger = logging.getLogger("ayush_emr.fhir.problem_list")

NAMASTE_SYSTEM = "http://namaste.ayush.gov.in"
TM2_SYSTEM = "http://id.who.int/icd/release/11/mms"
BIO_SYSTEM = "http://id.who.int/icd/release/11/mms/biomedical"


@dataclass
class DoubleCodingRequest:
    """
    All information required to perform a double-coding decision.
    Caller supplies patient / encounter identifiers and the source_term
    looked up by the clinician.  Actual codes are resolved deterministically
    from the database.
    """
    patient_reference: str              # "Patient/<id>"
    source_term: str                    # NAMASTE transliterated code or lookup term
    encounter_reference: Optional[str] = None
    onset_datetime: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class DoubleCodingResult:
    condition: Condition
    bundle: dict
    validation: BundleValidationResult
    concept_found: bool
    tm2_mapped: bool
    biomedicine_mapped: bool
    missing_biomedical_mapping: bool   # True = no bio code; condition is still valid
    diagnosis_detail: TraditionalDiagnosis


class ProblemListService:
    """
    Orchestrates the double-coding workflow without embedding code-selection
    logic in the route layer.
    """

    def __init__(self) -> None:
        self._builder = ConditionBuilder()

    def resolve_and_build(
        self,
        request: DoubleCodingRequest,
        db: Session,
        namaste_version: Optional[str] = None,
        tm2_version: Optional[str] = None,
        biomedicine_version: Optional[str] = None,
        mapping_version: Optional[str] = None,
    ) -> DoubleCodingResult:
        """
        Main entry point for the problem-list workflow.

        Steps
        -----
        1. Query TerminologyConcept by source_term / code / tm2_code
        2. Build TraditionalDiagnosis from authoritative DB columns
        3. Build FHIR Condition (double/triple coded with version provenance)
        4. Build FHIR Bundle wrapping the Condition
        5. Validate the Bundle
        6. Return structured result
        """
        concept = self._resolve_concept(request.source_term, db)
        concept_found = concept is not None

        if concept:
            diagnosis = TraditionalDiagnosis(
                source_term=concept.source_term or concept.code or request.source_term,
                display=concept.display or concept.english or request.source_term,
                namaste_system=concept.system or NAMASTE_SYSTEM,
                namaste_version=namaste_version or concept.source_version or "2024-v1",
                tm2_code=concept.tm2_code,
                tm2_display=concept.tm2_display,
                tm2_version=tm2_version or "2024-01" if concept.tm2_code else None,
                biomedicine_code=concept.biomedicine_code,  # null = NOT fabricated
                biomedicine_display=concept.biomedicine_display,
                biomedicine_version=biomedicine_version,
                mapping_source=concept.mapping_source or "authoritative-db",
                mapping_version=mapping_version or concept.mapping_version or "1.0",
                mapping_relationship=concept.mapping_relationship,
            )
        else:
            # Concept not found in DB: use source_term as NAMASTE code safely
            logger.warning(
                "Concept '%s' not found in DB — building NAMASTE-only condition",
                request.source_term,
            )
            diagnosis = TraditionalDiagnosis(
                source_term=request.source_term,
                display=request.source_term,
                namaste_version=namaste_version or "2024-v1",
                tm2_version=tm2_version,
                biomedicine_version=biomedicine_version,
                mapping_source="unmapped",
                mapping_version=mapping_version,
            )

        context = EncounterContext(
            patient_reference=request.patient_reference,
            encounter_reference=request.encounter_reference,
            onset_datetime=request.onset_datetime,
        )

        condition = self._builder.build(diagnosis, context)

        # Extract patient_id from "Patient/<id>" format
        patient_id = request.patient_reference.split("/")[-1]
        encounter_id = (
            request.encounter_reference.split("/")[-1]
            if request.encounter_reference else None
        )

        bundle_dict = build_double_coding_bundle(
            patient_id=patient_id,
            conditions=[condition],
            encounter_id=encounter_id,
        )

        validation = validate_bundle(bundle_dict)

        return DoubleCodingResult(
            condition=condition,
            bundle=bundle_dict,
            validation=validation,
            concept_found=concept_found,
            tm2_mapped=bool(diagnosis.tm2_code),
            biomedicine_mapped=bool(diagnosis.biomedicine_code),
            missing_biomedical_mapping=not bool(diagnosis.biomedicine_code),
            diagnosis_detail=diagnosis,
        )

    def persist_double_coding(
        self,
        result: DoubleCodingResult,
        db: Session,
        patient_id: str,
        encounter_id: Optional[str] = None,
    ) -> tuple[FHIRBundleModel, ClinicalCondition]:
        """
        Persist both the full FHIR Bundle and the ClinicalCondition entity
        preserving version and provenance metadata for historical reproducibility.
        """
        bundle_id = result.bundle.get("id") or str(uuid.uuid4())
        db_bundle = FHIRBundleModel(
            bundle_id=bundle_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            raw_payload=result.bundle,
            transformed_payload=None,
            status="processed",
        )
        db.add(db_bundle)

        diag = result.diagnosis_detail
        cond_id = result.condition.id or str(uuid.uuid4())
        db_condition = ClinicalCondition(
            condition_id=cond_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            bundle_id=bundle_id,
            source_term=diag.source_term,
            display=diag.display,
            namaste_system=diag.namaste_system,
            namaste_version=diag.namaste_version,
            tm2_code=diag.tm2_code,
            tm2_display=diag.tm2_display,
            tm2_version=diag.tm2_version,
            biomedicine_code=diag.biomedicine_code,
            biomedicine_display=diag.biomedicine_display,
            biomedicine_version=diag.biomedicine_version,
            mapping_source=diag.mapping_source,
            mapping_version=diag.mapping_version,
            mapping_relationship=diag.mapping_relationship,
            clinical_status="active",
            verification_status="confirmed",
            onset_datetime=result.condition.onsetDateTime,
            fhir_payload=result.condition.model_dump(exclude_none=True),
        )
        db.add(db_condition)
        db.commit()
        db.refresh(db_bundle)
        db.refresh(db_condition)

        return db_bundle, db_condition

    def get_patient_problem_list(
        self, patient_id: str, db: Session
    ) -> List[ClinicalCondition]:
        """Fetch all stored clinical conditions for a given patient."""
        return (
            db.query(ClinicalCondition)
            .filter(ClinicalCondition.patient_id == patient_id)
            .order_by(ClinicalCondition.created_at.desc())
            .all()
        )

    # ── private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_concept(source_term: str, db: Session) -> Optional[TerminologyConcept]:
        """Look up concept by source_term, code, or tm2_code."""
        return (
            db.query(TerminologyConcept)
            .filter(
                (TerminologyConcept.source_term == source_term)
                | (TerminologyConcept.code == source_term)
                | (TerminologyConcept.tm2_code == source_term)
            )
            .first()
        )


_service = ProblemListService()


def get_problem_list_service() -> ProblemListService:
    return _service
