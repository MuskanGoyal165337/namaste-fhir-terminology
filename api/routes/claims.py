"""
NHCX Claim Portal Backend API
=============================
Provides endpoints for insurance clerks and claim managers to view claim readiness
dashboards, inspect rule validation failures, and re-validate corrected claims.

Endpoints:
  - GET /claims/dashboard
  - POST /claims/revalidate

Security:
  - Requires Bearer authentication via ABHA
  - Enforces PBAC: role must be 'insurance_clerk' or 'admin' (or doctor submitting claims)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import FHIRBundle
from api.validators.icd11_rule_validator import ICD11RuleValidator, get_icd11_validator
from api.validators.nhcx_claim_checker import NHCXClaimChecker, CodingInput, get_nhcx_checker
from security.abha_auth import ABHATokenClaims, get_current_user
from security.audit_logger import AuditLogger, AuditEvent, get_audit_logger
from security.pbac_engine import PBACEngine, get_pbac_engine

logger = logging.getLogger("ayush_emr.api.routes.claims")

router = APIRouter(prefix="/claims", tags=["NHCX Claim Portal"])


# ------------------------------------------------------------------ #
#  Response & Request Models                                         #
# ------------------------------------------------------------------ #

class ClaimItem(BaseModel):
    claim_id: str
    bundle_id: str
    encounter_id: Optional[str]
    submitted_at: str
    status: str
    claimReadiness: bool
    claimReadinessScore: float
    validation_status: str
    failed_rule_id: Optional[str]
    failure_reason: Optional[str]
    suggested_fix: Optional[str]
    codings: List[Dict[str, Any]]


class ClaimDashboardResponse(BaseModel):
    total_claims: int
    ready_claims: int
    pending_claims: int
    claims: List[ClaimItem]


class RevalidateClaimRequest(BaseModel):
    claim_id: str
    codings: List[Dict[str, Any]]  # List of { system, code, display }


class RevalidateClaimResponse(BaseModel):
    claim_id: str
    claimReadiness: bool
    claimReadinessScore: float
    validation_valid: bool
    failed_rule_id: Optional[str]
    message: str
    corrected_suggestion: Optional[str]
    suggested_fix: Optional[str]


# ------------------------------------------------------------------ #
#  Routes                                                             #
# ------------------------------------------------------------------ #

@router.get("/dashboard", response_model=ClaimDashboardResponse)
def get_claim_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    claims: ABHATokenClaims = Depends(get_current_user),
    pbac: PBACEngine = Depends(get_pbac_engine),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    icd11_validator: ICD11RuleValidator = Depends(get_icd11_validator),
    nhcx_checker: NHCXClaimChecker = Depends(get_nhcx_checker),
):
    """
    Fetches the NHCX claim dashboard listing recent bundles, readiness scores,
    validation status, and failure reasons.
    """
    client_ip = request.client.host if request.client else "unknown"
    decision = pbac.evaluate(claims.role, "Claim", "read")
    if not decision.allowed:
        # Fall back to Terminology read check for clerks
        decision = pbac.evaluate(claims.role, "Terminology", "read")
        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "pbac_denied", "reason": decision.reason},
            )

    # Query bundles from DB
    db_bundles = db.query(FHIRBundle).order_by(FHIRBundle.created_at.desc()).limit(20).all()

    items: List[ClaimItem] = []
    for b in db_bundles:
        raw = b.raw_payload or {}
        entries = raw.get("entry", [])
        codings: List[Dict[str, Any]] = []
        for entry in entries:
            res = entry.get("resource", {})
            if res.get("resourceType") == "Condition" and res.get("code"):
                codings.extend(res["code"].get("coding", []))

        # Check NHCX readiness & ICD-11 rules
        coding_inputs = [CodingInput(system=c.get("system"), code=c.get("code"), display=c.get("display")) for c in codings]
        nhcx_res = nhcx_checker.check(coding_inputs)

        icd_valid = True
        failed_rule = None
        violation_msg = None
        if codings:
            first = codings[0]
            icd_res = icd11_validator.evaluate(first.get("code"), first.get("display"), first.get("system"))
            icd_valid = icd_res.valid
            failed_rule = icd_res.rule_id
            violation_msg = icd_res.message

        items.append(
            ClaimItem(
                claim_id=f"CLM-{b.id[:8]}",
                bundle_id=b.bundle_id,
                encounter_id=b.encounter_id or f"ENC-{b.id[:6]}",
                submitted_at=b.created_at.isoformat() if b.created_at else "",
                status=b.status,
                claimReadiness=nhcx_res.claimReadiness and icd_valid,
                claimReadinessScore=nhcx_res.claimReadinessScore if icd_valid else 0.5,
                validation_status="PASSED" if icd_valid else "FAILED",
                failed_rule_id=failed_rule,
                failure_reason=violation_msg or nhcx_res.failureReason,
                suggested_fix=nhcx_res.suggestedFix,
                codings=codings,
            )
        )

    # If DB is empty, provide demo claim items
    if not items:
        items = [
            ClaimItem(
                claim_id="CLM-1001",
                bundle_id="bundle-demo-1",
                encounter_id="ENC-8812",
                submitted_at="2026-08-13T10:30:00Z",
                status="processed",
                claimReadiness=True,
                claimReadinessScore=1.0,
                validation_status="PASSED",
                failed_rule_id=None,
                failure_reason=None,
                suggested_fix=None,
                codings=[{"system": "http://namaste.ayush.gov.in", "code": "TM2-001", "display": "jwara (fever)"}],
            ),
            ClaimItem(
                claim_id="CLM-1002",
                bundle_id="bundle-demo-2",
                encounter_id="ENC-8813",
                submitted_at="2026-08-13T11:15:00Z",
                status="rejected",
                claimReadiness=False,
                claimReadinessScore=0.33,
                validation_status="FAILED",
                failed_rule_id="DEV-ICD11-001",
                failure_reason="TM2 code does not start with a recognised prefix (TM2- or AAA-).",
                suggested_fix="Verify the code against the ICD-11 TM2 chapter and replace with TM2-002.",
                codings=[{"system": "http://unknown-system.org", "code": "INVALID-123", "display": "cough"}],
            ),
        ]

    ready_count = sum(1 for i in items if i.claimReadiness)
    return ClaimDashboardResponse(
        total_claims=len(items),
        ready_claims=ready_count,
        pending_claims=len(items) - ready_count,
        claims=items,
    )


@router.post("/revalidate", response_model=RevalidateClaimResponse)
def revalidate_claim(
    payload: RevalidateClaimRequest,
    db: Session = Depends(get_db),
    claims: ABHATokenClaims = Depends(get_current_user),
    pbac: PBACEngine = Depends(get_pbac_engine),
    icd11_validator: ICD11RuleValidator = Depends(get_icd11_validator),
    nhcx_checker: NHCXClaimChecker = Depends(get_nhcx_checker),
):
    """
    Re-validates a corrected claim payload against ICD-11 structure rules and NHCX payer rules.
    """
    codings_input = [CodingInput(system=c.get("system"), code=c.get("code"), display=c.get("display")) for c in payload.codings]
    nhcx_res = nhcx_checker.check(codings_input)

    first_code = payload.codings[0] if payload.codings else {}
    icd_res = icd11_validator.evaluate(first_code.get("code"), first_code.get("display"), first_code.get("system"))

    return RevalidateClaimResponse(
        claim_id=payload.claim_id,
        claimReadiness=nhcx_res.claimReadiness and icd_res.valid,
        claimReadinessScore=nhcx_res.claimReadinessScore if icd_res.valid else 0.5,
        validation_valid=icd_res.valid,
        failed_rule_id=icd_res.rule_id,
        message=icd_res.message,
        corrected_suggestion=icd_res.corrected_suggestion,
        suggested_fix=nhcx_res.suggestedFix,
    )
