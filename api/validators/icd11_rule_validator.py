"""
ICD-11 Rule Validator
=====================
Validates Condition codings against a structured ICD-11 rule file.

IMPORTANT: The default rule file (icd11_rules.json) contains DEVELOPMENT /
TEST rules only. These are clearly labelled and NOT official ICD-11 validation
rules. Production deployments should set the ICD11_RULES_PATH environment
variable to point to an authoritative rule file.

Rule conditions supported:
  - code_prefix           : code must start with an allowed prefix
  - display_not_empty     : display name must be present
  - code_required_when_system : if system is set, code must be set too

Returns a ValidationResult with:
  valid                 : bool
  rule_id               : which rule fired (or None)
  message               : human-readable explanation
  corrected_suggestion  : optional suggested fix
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger("ayush_emr.api.validators.icd11_rule_validator")

DEFAULT_RULES_PATH = Path(__file__).parent / "rules" / "icd11_rules.json"


# ------------------------------------------------------------------ #
#  Result model                                                       #
# ------------------------------------------------------------------ #

class ValidationResult(BaseModel):
    valid: bool
    rule_id: Optional[str] = None
    message: str
    corrected_suggestion: Optional[str] = None
    rule_source: str = "development"  # always expose rule provenance


# ------------------------------------------------------------------ #
#  Validator                                                          #
# ------------------------------------------------------------------ #

class ICD11RuleValidator:
    """
    Loads an ICD-11 rule file and evaluates codings against it.

    The validator is intentionally conservative:
      - It only flags clear violations of the rules in the loaded file.
      - It does NOT fabricate ICD-11 codes or biomedical classifications.
      - Rule source is always declared in the result.
    """

    def __init__(self, rules_path: Optional[Path] = None) -> None:
        path_str = os.environ.get("ICD11_RULES_PATH")
        self._path = Path(path_str) if path_str else (rules_path or DEFAULT_RULES_PATH)
        self._rules: List[Dict[str, Any]] = []
        self._rule_source: str = "development"
        self._version: str = "unknown"
        self._load()

    def _load(self) -> None:
        with open(self._path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self._rules = data.get("rules", [])
        self._rule_source = data.get("rule_source", "development")
        self._version = data.get("version", "unknown")
        logger.info(
            f"ICD-11 rules loaded: {len(self._rules)} rules, "
            f"source={self._rule_source}, version={self._version}"
        )

    def reload(self) -> None:
        self._load()

    def evaluate(
        self,
        code: Optional[str],
        display: Optional[str],
        system: Optional[str] = None,
    ) -> ValidationResult:
        """
        Evaluate a single code+display pair against all rules.
        Returns on the first failing rule (fail-fast).
        If all rules pass, returns valid=True.
        """
        for rule in self._rules:
            result = self._apply_rule(rule, code, display, system)
            if result is not None:
                return result

        return ValidationResult(
            valid=True,
            message="All validation rules passed.",
            rule_source=self._rule_source,
        )

    def _apply_rule(
        self,
        rule: Dict[str, Any],
        code: Optional[str],
        display: Optional[str],
        system: Optional[str],
    ) -> Optional[ValidationResult]:
        """Apply a single rule. Returns ValidationResult on violation, None on pass."""
        condition = rule.get("condition")
        rule_id = rule.get("rule_id", "UNKNOWN")
        severity = rule.get("severity", "error")
        message = rule.get("message", "Rule violation.")
        suggestion = rule.get("corrected_suggestion")

        if condition == "code_prefix":
            allowed = rule.get("allowed_prefixes", [])
            if code and not any(code.startswith(p) for p in allowed):
                return ValidationResult(
                    valid=(severity != "error"),
                    rule_id=rule_id,
                    message=message,
                    corrected_suggestion=suggestion,
                    rule_source=self._rule_source,
                )

        elif condition == "display_not_empty":
            if not display or not display.strip():
                return ValidationResult(
                    valid=False,
                    rule_id=rule_id,
                    message=message,
                    corrected_suggestion=suggestion,
                    rule_source=self._rule_source,
                )

        elif condition == "code_required_when_system":
            if system and not code:
                return ValidationResult(
                    valid=(severity != "error"),
                    rule_id=rule_id,
                    message=message,
                    corrected_suggestion=suggestion,
                    rule_source=self._rule_source,
                )

        return None  # Rule passed

    @property
    def rule_source(self) -> str:
        return self._rule_source

    @property
    def version(self) -> str:
        return self._version


# ------------------------------------------------------------------ #
#  FastAPI dependency                                                 #
# ------------------------------------------------------------------ #

_validator_singleton: Optional[ICD11RuleValidator] = None


def get_icd11_validator() -> ICD11RuleValidator:
    global _validator_singleton
    if _validator_singleton is None:
        _validator_singleton = ICD11RuleValidator()
    return _validator_singleton
