"""
NHCX Claim Checker
==================
Validates a set of Condition codings for NHCX claim readiness.

IMPORTANT: The default rules (nhcx_payer_rules.json) are DEVELOPMENT / TEST
rules only. They are NOT official NHCX payer rules. Set NHCX_RULES_PATH to
point to authoritative rules in production.

Returns ClaimCheckResult with:
  claimReadiness       : bool   — True if all error-level rules pass
  claimReadinessScore  : float  — fraction of rules passed (0.0–1.0)
  failureReason        : str    — description of first failure, or None
  suggestedFix         : str    — suggested remediation, or None
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger("ayush_emr.api.validators.nhcx_claim_checker")

DEFAULT_RULES_PATH = Path(__file__).parent / "rules" / "nhcx_payer_rules.json"


# ------------------------------------------------------------------ #
#  Result model                                                       #
# ------------------------------------------------------------------ #

class ClaimCheckResult(BaseModel):
    claimReadiness: bool
    claimReadinessScore: float
    failureReason: Optional[str] = None
    suggestedFix: Optional[str] = None
    rule_source: str = "development"


# ------------------------------------------------------------------ #
#  Coding input model (lightweight, avoids circular imports)         #
# ------------------------------------------------------------------ #

class CodingInput(BaseModel):
    system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None


# ------------------------------------------------------------------ #
#  Checker                                                            #
# ------------------------------------------------------------------ #

class NHCXClaimChecker:
    """
    Evaluates a list of Condition codings for NHCX claim readiness.
    Loaded from nhcx_payer_rules.json (default: development rules only).
    """

    def __init__(self, rules_path: Optional[Path] = None) -> None:
        path_str = os.environ.get("NHCX_RULES_PATH")
        self._path = Path(path_str) if path_str else (rules_path or DEFAULT_RULES_PATH)
        self._rules: List[Dict[str, Any]] = []
        self._rule_source: str = "development"
        self._load()

    def _load(self) -> None:
        with open(self._path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self._rules = data.get("rules", [])
        self._rule_source = data.get("rule_source", "development")
        logger.info(
            f"NHCX rules loaded: {len(self._rules)} rules, "
            f"source={self._rule_source}"
        )

    def reload(self) -> None:
        self._load()

    def check(self, codings: List[CodingInput]) -> ClaimCheckResult:
        """
        Evaluate a list of codings against all NHCX rules.

        Scoring:
          - Each rule that passes adds 1/N to claimReadinessScore.
          - claimReadiness=False if any error-level rule fails.
          - failureReason and suggestedFix populated on first error failure.
        """
        if not self._rules:
            return ClaimCheckResult(
                claimReadiness=True,
                claimReadinessScore=1.0,
                rule_source=self._rule_source,
            )

        passed = 0
        first_error_reason: Optional[str] = None
        first_error_fix: Optional[str] = None
        claim_ready = True

        for rule in self._rules:
            ok = self._apply_rule(rule, codings)
            if ok:
                passed += 1
            else:
                severity = rule.get("severity", "error")
                if severity == "error" and first_error_reason is None:
                    first_error_reason = rule.get("message")
                    first_error_fix = rule.get("suggestedFix")
                    claim_ready = False

        score = round(passed / len(self._rules), 3)

        return ClaimCheckResult(
            claimReadiness=claim_ready,
            claimReadinessScore=score,
            failureReason=first_error_reason,
            suggestedFix=first_error_fix,
            rule_source=self._rule_source,
        )

    def _apply_rule(
        self, rule: Dict[str, Any], codings: List[CodingInput]
    ) -> bool:
        condition = rule.get("condition")

        if condition == "has_condition_coding":
            return len(codings) > 0

        elif condition == "recognised_system_uri":
            allowed = set(rule.get("allowed_systems", []))
            return all(
                (c.system in allowed if c.system else True)
                for c in codings
            )

        elif condition == "tm2_code_present":
            prefixes = rule.get("tm2_prefixes", [])
            return any(
                c.code and any(c.code.startswith(p) for p in prefixes)
                for c in codings
            )

        # Unknown condition → pass (non-breaking)
        return True


# ------------------------------------------------------------------ #
#  FastAPI dependency                                                 #
# ------------------------------------------------------------------ #

_checker_singleton: Optional[NHCXClaimChecker] = None


def get_nhcx_checker() -> NHCXClaimChecker:
    global _checker_singleton
    if _checker_singleton is None:
        _checker_singleton = NHCXClaimChecker()
    return _checker_singleton
