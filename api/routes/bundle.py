"""
POST /Bundle — FHIR R4 Bundle Ingestion with Full Validation Pipeline
======================================================================
Accepts a FHIR R4 Bundle containing Condition resources.

Processing pipeline (all steps before DB commit):
  1. FHIR structure validation
  2. ABHA authentication (Bearer token)
  3. PBAC: role must be 'doctor' or 'admin'
  4. ICD-11 rule validation of Condition codings
  5. NHCX claim readiness check
  6. Correction logging (if corrected_code provided)
  7. Audit logging
  8. PostgreSQL transaction (FHIRBundle row)
  9. Commit

Rolls back on any exception. Returns structured response including
validation details, claim readiness, and correction flag.
"""
from __future__ import annotations

import datetime
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import FHIRBundle as FHIRBundleModel
from api.models.fhir_models import FHIRBundle
from api.models.response_models import BundlePostResponse, ClaimCheck, ValidationDetail
from api.validators.icd11_rule_validator import ICD11RuleValidator, get_icd11_validator
from api.validators.nhcx_claim_checker import NHCXClaimChecker, CodingInput, get_nhcx_checker
from api.correction_logger import CorrectionLogger, CorrectionPayload, get_correction_logger
from security.abha_auth import ABHATokenClaims, get_current_user
from security.audit_logger import AuditLogger, AuditEvent, get_audit_logger
from security.pbac_engine import PBACEngine, get_pbac_engine

logger = logging.getLogger("ayush_emr.api.routes.bundle")

router = APIRouter(tags=["FHIR"])


# ------------------------------------------------------------------ #
#  Request wrapper                                                    #
# ------------------------------------------------------------------ #

class BundlePostRequest(BaseModel):
    """Wraps the FHIR Bundle payload with optional correction metadata."""
    bundle: FHIRBundle
    # Optional: if practitioner corrects an AI-suggested code
    input_symptoms: Optional[str] = None
    suggested_code: Optional[str] = None
    corrected_code: Optional[str] = None
    session_id: Optional[str] = None


# ------------------------------------------------------------------ #
#  Route                                                              #
# ------------------------------------------------------------------ #

@router.post("/Bundle", response_model=BundlePostResponse, status_code=status.HTTP_201_CREATED)
def post_bundle(
    payload: BundlePostRequest,
    request: Request,
    db: Session = Depends(get_db),
    claims: ABHATokenClaims = Depends(get_current_user),
    pbac: PBACEngine = Depends(get_pbac_engine),
    icd11_validator: ICD11RuleValidator = Depends(get_icd11_validator),
    nhcx_checker: NHCXClaimChecker = Depends(get_nhcx_checker),
    correction_logger: CorrectionLogger = Depends(get_correction_logger),
    audit_logger: AuditLogger = Depends(get_audit_logger),
):
    """
    Ingest a FHIR R4 Bundle through the full validation pipeline.
    Requires Bearer authentication + 'doctor' or 'admin' role.
    """
    client_ip = request.client.host if (request and getattr(request, "client", None)) else "unknown"
    bundle = payload.bundle


    # ── Step 1: FHIR structure validation ─────────────────────────
    fhir_errors = bundle.validate_structure()
    if fhir_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "fhir_validation_failed", "errors": fhir_errors},
        )

    # ── Step 2: Auth already done by Depends(get_current_user) ────

    # ── Step 3: PBAC check ────────────────────────────────────────
    pbac_decision = pbac.evaluate(claims.role, "Condition", "write")
    if not pbac_decision.allowed:
        audit_logger.log(
            db,
            AuditEvent(
                event_type="PBAC_DENY",
                actor_id=claims.sub,
                practitioner_id=claims.practitioner_id,
                action="write",
                client_ip=client_ip,
                details={"reason": pbac_decision.reason},
            ),
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "pbac_denied", "reason": pbac_decision.reason},
        )

    # ── Step 4: ICD-11 rule validation ────────────────────────────
    conditions = bundle.get_conditions()
    primary_coding = None
    if conditions:
        primary_coding = conditions[0].get_primary_coding()

    icd_result = icd11_validator.evaluate(
        code=primary_coding.code if primary_coding else None,
        display=primary_coding.display if primary_coding else None,
        system=primary_coding.system if primary_coding else None,
    )

    validation_detail = ValidationDetail(
        valid=icd_result.valid,
        rule_id=icd_result.rule_id,
        message=icd_result.message,
        corrected_suggestion=icd_result.corrected_suggestion,
    )

    if not icd_result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "icd11_rule_violation",
                "rule_id": icd_result.rule_id,
                "message": icd_result.message,
                "corrected_suggestion": icd_result.corrected_suggestion,
            },
        )

    # ── Step 5: NHCX claim readiness ──────────────────────────────
    codings_input = []
    for cond in conditions:
        if cond.code:
            for cod in cond.code.coding:
                codings_input.append(CodingInput(
                    system=cod.system,
                    code=cod.code,
                    display=cod.display,
                ))

    claim_result = nhcx_checker.check(codings_input)
    claim_check = ClaimCheck(
        claimReadiness=claim_result.claimReadiness,
        claimReadinessScore=claim_result.claimReadinessScore,
        failureReason=claim_result.failureReason,
        suggestedFix=claim_result.suggestedFix,
    )

    # ── Step 6: Correction logging ────────────────────────────────
    correction_logged = False
    if payload.corrected_code:
        correction_logger.log_correction(
            db,
            CorrectionPayload(
                input_symptoms=payload.input_symptoms or "",
                suggested_code=payload.suggested_code,
                corrected_code=payload.corrected_code,
                practitioner_id=claims.practitioner_id or claims.sub,
                session_id=payload.session_id,
            ),
        )
        correction_logged = True

    # ── Step 7: Audit logging ─────────────────────────────────────
    audit_row = audit_logger.log(
        db,
        AuditEvent(
            event_type="FHIR_TRANSFORM",
            actor_id=claims.sub,
            practitioner_id=claims.practitioner_id,
            patient_consent_id=claims.patient_consent_id,
            action="write",
            client_ip=client_ip,
            details={
                "bundle_type": bundle.type,
                "entry_count": len(bundle.entry),
                "claim_ready": claim_result.claimReadiness,
            },
        ),
    )

    # ── Step 8: Persist FHIRBundle ────────────────────────────────
    bundle_id = bundle.id or str(uuid.uuid4())
    db_bundle = FHIRBundleModel(
        bundle_id=bundle_id,
        patient_id=None,          # no patient PII stored
        encounter_id=None,
        raw_payload=bundle.model_dump(),
        transformed_payload=None,
        status="processed",
    )
    db.add(db_bundle)

    # ── Step 9: Commit ────────────────────────────────────────────
    db.commit()

    return BundlePostResponse(
        bundle_id=bundle_id,
        status="processed",
        validation=validation_detail,
        claimReadiness=claim_check,
        correction_logged=correction_logged,
        audit_id=audit_row.id,
    )
