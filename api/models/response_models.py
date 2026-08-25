"""
API response models — typed, structured output for all Layer 4 routes.

All biomedicine_code fields are Optional[str] and will be null for the current
dataset.  They MUST NOT be fabricated.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class XAIWeight(BaseModel):
    token: str
    score: float


class ExpandResult(BaseModel):
    """Single result from GET /$expand."""
    # ── Core terminology fields ─────────────────────────────────────────────
    source_term: str
    display_name: str
    tm2_code: Optional[str] = None
    tm2_display: Optional[str] = None          # ICD-11 TM2 display text
    system: str
    language: Optional[str] = None

    # ── Source provenance ───────────────────────────────────────────────────
    source_system: Optional[str] = None        # Originating system URI
    source_version: Optional[str] = None       # Terminology release version

    # ── WHO International Standard Terminology ──────────────────────────────
    who_term_code: Optional[str] = None        # null unless authoritatively mapped
    who_term_display: Optional[str] = None

    # ── ICD-11 Biomedicine ──────────────────────────────────────────────────
    # Always null for current dataset — NEVER fabricated.
    icd11_code: Optional[str] = None           # legacy alias (kept for backward compat)
    biomedicine_code: Optional[str] = None     # null unless supplied by authoritative source
    biomedicine_display: Optional[str] = None

    # ── Mapping metadata ────────────────────────────────────────────────────
    mapping_relationship: Optional[str] = None  # MappingRelationship constant
    mapping_status: Optional[str] = None        # MappingStatus constant
    mapping_source: Optional[str] = None        # provenance of mapping

    # ── Search metadata ─────────────────────────────────────────────────────
    similarity: Optional[float] = None          # null for exact/substring
    match_method: str                            # "exact" | "substring" | "semantic"
    xai_weights: Optional[List[XAIWeight]] = None  # only for semantic


class ExpandResponse(BaseModel):
    query: str
    lang: Optional[str] = None
    system_filter: Optional[str] = None
    total: int
    results: List[ExpandResult]


class TranslateResult(BaseModel):
    """Result from POST /$translate."""
    source_code: str
    source_term: Optional[str] = None
    display_name: Optional[str] = None
    system: Optional[str] = None
    tm2_code: Optional[str] = None
    tm2_display: Optional[str] = None          # ICD-11 TM2 display text

    # ── ICD-11 Biomedicine ──────────────────────────────────────────────────
    biomedicine_code: Optional[str] = None
    biomedicine_display: Optional[str] = None

    # ── Mapping metadata ────────────────────────────────────────────────────
    mapping_relationship: Optional[str] = None
    target_system: str
    confidence: float
    used_fallback: bool
    concept_map_version: Optional[str] = None
    mapping_status: Optional[str] = None
    mapping_source: Optional[str] = None       # provenance of the mapping
    mapping_version: Optional[str] = None      # version of mapping ruleset


class ValidationDetail(BaseModel):
    valid: bool
    rule_id: Optional[str] = None
    message: str
    corrected_suggestion: Optional[str] = None


class ClaimCheck(BaseModel):
    claimReadiness: bool
    claimReadinessScore: float                  # 0.0 – 1.0
    failureReason: Optional[str] = None
    suggestedFix: Optional[str] = None


class BundlePostResponse(BaseModel):
    bundle_id: str
    status: str                                  # "processed" | "failed" | "pending"
    validation: ValidationDetail
    claimReadiness: ClaimCheck
    correction_logged: bool
    audit_id: Optional[str] = None
