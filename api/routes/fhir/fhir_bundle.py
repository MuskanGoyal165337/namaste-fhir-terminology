"""
api/routes/fhir/fhir_bundle.py
===============================
FHIR R4 Bundle and Condition Ingestion & Problem List Routes:
  POST /fhir/Bundle               — Accept & validate raw or wrapped FHIR R4 Bundle
  POST /fhir/Condition            — Create a double-coded FHIR Condition
  POST /fhir/problem-list/double-code — Clinician double-coding workflow
  GET  /fhir/problem-list/{patient_id} — Retrieve patient's problem list
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import FHIRBundle as FHIRBundleModel, ClinicalCondition
from fhir.condition import (
    ConditionBuilder,
    TraditionalDiagnosis,
    EncounterContext,
)
from fhir.bundle import build_double_coding_bundle
from fhir.problem_list import (
    DoubleCodingRequest,
    ProblemListService,
    get_problem_list_service,
)
from fhir.validation import validate_bundle, BundleValidator
from api.models.fhir_models import Condition, FHIRBundle
from api.validators.icd11_rule_validator import ICD11RuleValidator, get_icd11_validator
from api.validators.nhcx_claim_checker import NHCXClaimChecker, CodingInput, get_nhcx_checker
from security.audit_logger import AuditLogger, AuditEvent, get_audit_logger

logger = logging.getLogger("ayush_emr.api.fhir.bundle")

router = APIRouter(prefix="/fhir", tags=["FHIR Clinical"])


# ──────────────────────────────────────────────────────────────────────────────
# Pydantic Request & Response schemas
# ──────────────────────────────────────────────────────────────────────────────

class DoubleCodePayload(BaseModel):
    """Payload to trigger clinician double-coding workflow."""
    patient_id: str = Field(..., description="Patient ID e.g. '12345' or 'Patient/12345'")
    source_term: str = Field(..., description="Traditional terminology term or code (e.g. 'udAnavAtakopaH')")
    encounter_id: Optional[str] = Field(None, description="Optional Encounter ID")
    onset_datetime: Optional[str] = Field(None, description="ISO-8601 onset timestamp")
    namaste_version: Optional[str] = None
    tm2_version: Optional[str] = None
    biomedicine_version: Optional[str] = None
    mapping_version: Optional[str] = None
    persist: bool = Field(True, description="Whether to persist the Condition and Bundle in the DB")


class DoubleCodeResponse(BaseModel):
    """Response containing double-coded condition, bundle, and metadata."""
    condition: Dict[str, Any]
    bundle: Dict[str, Any]
    valid: bool
    concept_found: bool
    tm2_mapped: bool
    biomedicine_mapped: bool
    missing_biomedical_mapping: bool
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    persisted: bool = False
    bundle_id: Optional[str] = None
    condition_id: Optional[str] = None


class ProblemListItem(BaseModel):
    id: str
    condition_id: str
    patient_id: str
    encounter_id: Optional[str] = None
    source_term: str
    display: str
    namaste_system: str
    namaste_version: Optional[str] = None
    tm2_code: Optional[str] = None
    tm2_display: Optional[str] = None
    tm2_version: Optional[str] = None
    biomedicine_code: Optional[str] = None
    biomedicine_display: Optional[str] = None
    biomedicine_version: Optional[str] = None
    mapping_source: Optional[str] = None
    mapping_version: Optional[str] = None
    clinical_status: str
    verification_status: str
    fhir_payload: Dict[str, Any]


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/Bundle",
    status_code=status.HTTP_201_CREATED,
    summary="Accept and ingest a FHIR R4 Bundle (Patient, Encounter, Condition)",
)
def post_fhir_bundle(
    payload: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    icd11_validator: ICD11RuleValidator = Depends(get_icd11_validator),
    nhcx_checker: NHCXClaimChecker = Depends(get_nhcx_checker),
    audit_logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Accepts a standard FHIR R4 Bundle (or wrapped bundle object).
    Validates structure, required fields, coding systems, supported codes,
    and basic references.
    Rejects malformed or invalid Bundles with FHIR-compliant error responses.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Unwrap if wrapped as {"bundle": {...}}
    bundle_dict = payload.get("bundle", payload)

    # ── Step 1: Structural & FHIR Schema Validation ───────────────────────
    val_result = validate_bundle(bundle_dict)
    if not val_result.valid:
        outcome = val_result.to_fhir_operation_outcome()
        outcome["detail"] = {
            "error": "bundle_validation_failed",
            "errors": [e.message for e in val_result.errors],
        }
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=outcome,
        )

    # ── Step 2: Extract conditions & validate coding rules ────────────────
    entries = bundle_dict.get("entry", [])
    patient_id = None
    encounter_id = None
    conditions = []

    for entry in entries:
        res = entry.get("resource", {})
        rt = res.get("resourceType")
        if rt == "Patient":
            patient_id = res.get("id")
        elif rt == "Encounter":
            encounter_id = res.get("id")
        elif rt == "Condition":
            conditions.append(res)

    # Evaluate ICD-11 rules on Condition primary codings
    for cond in conditions:
        codings = cond.get("code", {}).get("coding", [])
        if codings:
            primary = codings[0]
            icd_res = icd11_validator.evaluate(
                code=primary.get("code"),
                display=primary.get("display"),
                system=primary.get("system"),
            )
            if not icd_res.valid:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "resourceType": "OperationOutcome",
                        "issue": [{
                            "severity": "error",
                            "code": "invalid",
                            "diagnostics": icd_res.message,
                        }],
                        "error": "icd11_rule_violation",
                        "rule_id": icd_res.rule_id,
                        "message": icd_res.message,
                    },
                )

    # ── Step 3: Check NHCX Claim Readiness ────────────────────────────────
    coding_inputs = []
    for cond in conditions:
        for c in cond.get("code", {}).get("coding", []):
            coding_inputs.append(CodingInput(
                system=c.get("system"),
                code=c.get("code"),
                display=c.get("display"),
            ))
    claim_check = nhcx_checker.check(coding_inputs)

    # ── Step 4: Persist Bundle ───────────────────────────────────────────
    bundle_id = bundle_dict.get("id") or str(uuid.uuid4())
    db_bundle = FHIRBundleModel(
        bundle_id=bundle_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        raw_payload=bundle_dict,
        status="processed",
    )
    db.add(db_bundle)

    # Also persist Condition resources into ClinicalCondition table
    for cond in conditions:
        cond_id = cond.get("id") or str(uuid.uuid4())
        codings = cond.get("code", {}).get("coding", [])
        
        # Extract NAMASTE, TM2, and Biomedicine codings
        namaste_code = None
        namaste_disp = None
        namaste_sys = "http://namaste.ayush.gov.in"
        tm2_c = None
        tm2_disp = None
        bio_c = None
        bio_disp = None

        for c in codings:
            sys = c.get("system", "")
            if "namaste" in sys or "ayush" in sys:
                namaste_code = c.get("code")
                namaste_disp = c.get("display")
                namaste_sys = sys
            elif "biomedical" in sys:
                bio_c = c.get("code")
                bio_disp = c.get("display")
            elif "mms" in sys or "icd" in sys:
                tm2_c = c.get("code")
                tm2_disp = c.get("display")

        source_term_val = namaste_code or (codings[0].get("code") if codings else "unknown")
        display_val = namaste_disp or cond.get("code", {}).get("text") or source_term_val

        # Extract subject patient id if not already extracted
        cond_patient_id = patient_id
        if not cond_patient_id:
            subj_ref = cond.get("subject", {}).get("reference", "")
            cond_patient_id = subj_ref.split("/")[-1] if subj_ref else "anonymous"

        db_cond = ClinicalCondition(
            condition_id=cond_id,
            patient_id=cond_patient_id,
            encounter_id=encounter_id,
            bundle_id=bundle_id,
            source_term=source_term_val,
            display=display_val,
            namaste_system=namaste_sys,
            tm2_code=tm2_c,
            tm2_display=tm2_disp,
            biomedicine_code=bio_c,
            biomedicine_display=bio_disp,
            clinical_status="active",
            verification_status="confirmed",
            onset_datetime=cond.get("onsetDateTime"),
            fhir_payload=cond,
        )
        db.add(db_cond)

    db.commit()

    # ── Step 5: Audit log ─────────────────────────────────────────────────
    audit_logger.log(
        db,
        AuditEvent(
            event_type="FHIR_BUNDLE_INGEST",
            actor_id="system",
            action="write",
            client_ip=client_ip,
            details={
                "bundle_id": bundle_id,
                "entry_count": len(entries),
                "condition_count": len(conditions),
                "claim_readiness": claim_check.claimReadiness,
            },
        ),
    )
    db.commit()

    return {
        "resourceType": "Bundle",
        "id": bundle_id,
        "status": "processed",
        "entry_count": len(entries),
        "validation": {
            "valid": True,
            "warnings": [w.message for w in val_result.warnings],
        },
        "claimReadiness": {
            "claimReadiness": claim_check.claimReadiness,
            "claimReadinessScore": claim_check.claimReadinessScore,
            "failureReason": claim_check.failureReason,
            "suggestedFix": claim_check.suggestedFix,
        },
    }


@router.post(
    "/problem-list/double-code",
    response_model=DoubleCodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clinician double-coding workflow: resolves concept, generates FHIR Condition & Bundle",
)
def double_code_diagnosis(
    payload: DoubleCodePayload,
    db: Session = Depends(get_db),
    service: ProblemListService = Depends(get_problem_list_service),
):
    """
    Executes the clinical double-coding workflow:
    1. Looks up traditional diagnosis
    2. Resolves TM2 mapping from DB
    3. Resolves Biomedical ICD-11 mapping from DB (never fabricated; omitted if not present)
    4. Builds a FHIR Condition / Problem List entry
    5. Builds a FHIR Bundle wrapping Patient, Encounter, and Condition
    6. Persists the record if persist=True
    """
    patient_ref = payload.patient_id if payload.patient_id.startswith("Patient/") else f"Patient/{payload.patient_id}"
    enc_ref = (
        payload.encounter_id
        if (not payload.encounter_id or payload.encounter_id.startswith("Encounter/"))
        else f"Encounter/{payload.encounter_id}"
    )

    req = DoubleCodingRequest(
        patient_reference=patient_ref,
        source_term=payload.source_term,
        encounter_reference=enc_ref,
        onset_datetime=payload.onset_datetime,
    )

    result = service.resolve_and_build(
        request=req,
        db=db,
        namaste_version=payload.namaste_version,
        tm2_version=payload.tm2_version,
        biomedicine_version=payload.biomedicine_version,
        mapping_version=payload.mapping_version,
    )

    bundle_id = None
    condition_id = result.condition.id

    if payload.persist:
        pid = payload.patient_id.split("/")[-1]
        eid = payload.encounter_id.split("/")[-1] if payload.encounter_id else None
        db_b, db_c = service.persist_double_coding(result, db, patient_id=pid, encounter_id=eid)
        bundle_id = db_b.bundle_id
        condition_id = db_c.condition_id

    return DoubleCodeResponse(
        condition=result.condition.model_dump(exclude_none=True),
        bundle=result.bundle,
        valid=result.validation.valid,
        concept_found=result.concept_found,
        tm2_mapped=result.tm2_mapped,
        biomedicine_mapped=result.biomedicine_mapped,
        missing_biomedical_mapping=result.missing_biomedical_mapping,
        warnings=[{"path": w.path, "message": w.message} for w in result.validation.warnings],
        persisted=payload.persist,
        bundle_id=bundle_id,
        condition_id=condition_id,
    )


@router.post(
    "/Condition",
    status_code=status.HTTP_201_CREATED,
    summary="Construct a FHIR Condition with double-coding from authoritative DB mappings",
)
def create_fhir_condition(
    payload: DoubleCodePayload,
    db: Session = Depends(get_db),
    service: ProblemListService = Depends(get_problem_list_service),
):
    """
    Constructs and returns a FHIR R4 Condition representation with double-coding.
    """
    patient_ref = payload.patient_id if payload.patient_id.startswith("Patient/") else f"Patient/{payload.patient_id}"
    enc_ref = (
        payload.encounter_id
        if (not payload.encounter_id or payload.encounter_id.startswith("Encounter/"))
        else f"Encounter/{payload.encounter_id}"
    )

    req = DoubleCodingRequest(
        patient_reference=patient_ref,
        source_term=payload.source_term,
        encounter_reference=enc_ref,
        onset_datetime=payload.onset_datetime,
    )

    result = service.resolve_and_build(
        request=req,
        db=db,
        namaste_version=payload.namaste_version,
        tm2_version=payload.tm2_version,
        biomedicine_version=payload.biomedicine_version,
        mapping_version=payload.mapping_version,
    )

    if payload.persist:
        pid = payload.patient_id.split("/")[-1]
        eid = payload.encounter_id.split("/")[-1] if payload.encounter_id else None
        service.persist_double_coding(result, db, patient_id=pid, encounter_id=eid)

    return result.condition.model_dump(exclude_none=True)


@router.get(
    "/problem-list/{patient_id}",
    response_model=List[ProblemListItem],
    summary="Get double-coded problem list for a patient",
)
def get_patient_problem_list(
    patient_id: str,
    db: Session = Depends(get_db),
    service: ProblemListService = Depends(get_problem_list_service),
):
    """
    Returns the stored problem list for a patient, including all double-coded
    mappings, version provenance, and full FHIR Condition payloads.
    """
    pid = patient_id.split("/")[-1]
    conditions = service.get_patient_problem_list(pid, db)
    return [
        ProblemListItem(
            id=c.id,
            condition_id=c.condition_id,
            patient_id=c.patient_id,
            encounter_id=c.encounter_id,
            source_term=c.source_term,
            display=c.display,
            namaste_system=c.namaste_system,
            namaste_version=c.namaste_version,
            tm2_code=c.tm2_code,
            tm2_display=c.tm2_display,
            tm2_version=c.tm2_version,
            biomedicine_code=c.biomedicine_code,
            biomedicine_display=c.biomedicine_display,
            biomedicine_version=c.biomedicine_version,
            mapping_source=c.mapping_source,
            mapping_version=c.mapping_version,
            clinical_status=c.clinical_status,
            verification_status=c.verification_status,
            fhir_payload=c.fhir_payload,
        )
        for c in conditions
    ]
