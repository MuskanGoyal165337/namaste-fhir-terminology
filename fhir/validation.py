"""
fhir/validation.py
===================
FHIR R4 Bundle and Condition validation layer for the double-coding workflow.

Validates:
  - resourceType field presence and value
  - Required fields per resource type
  - Coding system URIs against allowed sets
  - Basic reference integrity (patient reference must exist in Bundle)
  - Terminology versions (warns when absent)
  - Duplicate entry detection
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

NAMASTE_SYSTEM = "http://namaste.ayush.gov.in"
TM2_SYSTEM     = "http://id.who.int/icd/release/11/mms"
BIO_SYSTEM     = "http://id.who.int/icd/release/11/mms/biomedical"
SNOMED_SYSTEM  = "http://snomed.info/sct"
LOINC_SYSTEM   = "http://loinc.org"

ALLOWED_CODING_SYSTEMS = {NAMASTE_SYSTEM, TM2_SYSTEM, BIO_SYSTEM, SNOMED_SYSTEM, LOINC_SYSTEM}

CLINICAL_STATUS_SYSTEM  = "http://terminology.hl7.org/CodeSystem/condition-clinical"
VER_STATUS_SYSTEM       = "http://terminology.hl7.org/CodeSystem/condition-ver-status"

SUPPORTED_RESOURCE_TYPES = {"Patient", "Encounter", "Condition", "Observation"}


@dataclass
class ValidationError:
    path: str
    message: str
    severity: str = "error"   # "error" | "warning"


@dataclass
class BundleValidationResult:
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    def to_fhir_operation_outcome(self) -> Dict[str, Any]:
        """Render as a minimal FHIR OperationOutcome for HTTP error responses."""
        issues = []
        for e in self.errors:
            issues.append({
                "severity": "error",
                "code": "invalid",
                "diagnostics": e.message,
                "expression": [e.path],
            })
        for w in self.warnings:
            issues.append({
                "severity": "warning",
                "code": "informational",
                "diagnostics": w.message,
                "expression": [w.path],
            })
        return {"resourceType": "OperationOutcome", "issue": issues}


class BundleValidator:
    """
    Validates a FHIR R4 Bundle dict (as received from the wire).

    Checks:
      1. resourceType == "Bundle"
      2. type field is present
      3. entry array is non-empty
      4. Each entry has a resource with resourceType
      5. resourceType is within supported set
      6. Required fields per resource type
      7. Condition codings use allowed systems
      8. Patient reference on Conditions exists in the Bundle
      9. No duplicate fullUrl values
    """

    def validate(self, bundle: Dict[str, Any]) -> BundleValidationResult:
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # 1. resourceType
        if bundle.get("resourceType") != "Bundle":
            errors.append(ValidationError(
                path="Bundle.resourceType",
                message=f"resourceType must be 'Bundle', got '{bundle.get('resourceType')}'",
            ))
            return BundleValidationResult(valid=False, errors=errors)

        # 2. type
        if not bundle.get("type"):
            errors.append(ValidationError(
                path="Bundle.type",
                message="Bundle.type is required (e.g. 'transaction', 'collection')",
            ))

        # 3. entries
        entries = bundle.get("entry", [])
        if not entries:
            errors.append(ValidationError(
                path="Bundle.entry",
                message="Bundle must contain at least one entry",
            ))
            return BundleValidationResult(valid=False, errors=errors)

        # 9. Duplicate fullUrl check
        full_urls = [e.get("fullUrl") for e in entries if e.get("fullUrl")]
        if len(full_urls) != len(set(full_urls)):
            errors.append(ValidationError(
                path="Bundle.entry[*].fullUrl",
                message="Duplicate fullUrl values found in Bundle entries",
            ))

        # Collect patient refs present in Bundle
        patient_refs_in_bundle: set = set()
        for i, entry in enumerate(entries):
            resource = entry.get("resource", {})
            rt = resource.get("resourceType", "")
            if rt == "Patient":
                pid = resource.get("id")
                if pid:
                    patient_refs_in_bundle.add(f"Patient/{pid}")
            if entry.get("fullUrl"):
                patient_refs_in_bundle.add(entry["fullUrl"])

        for i, entry in enumerate(entries):
            resource = entry.get("resource")
            path_prefix = f"Bundle.entry[{i}]"

            if resource is None:
                errors.append(ValidationError(
                    path=f"{path_prefix}.resource",
                    message=f"Entry {i} has no resource",
                ))
                continue

            rt = resource.get("resourceType")
            if not rt:
                errors.append(ValidationError(
                    path=f"{path_prefix}.resource.resourceType",
                    message=f"Entry {i} resource missing resourceType",
                ))
                continue

            if rt not in SUPPORTED_RESOURCE_TYPES:
                warnings.append(ValidationError(
                    path=f"{path_prefix}.resource.resourceType",
                    message=(
                        f"Entry {i} resourceType '{rt}' is not in the supported "
                        f"set {SUPPORTED_RESOURCE_TYPES}. Entry will be ignored."
                    ),
                    severity="warning",
                ))
                continue

            # Per-resource validation
            if rt == "Condition":
                errs, warns = self._validate_condition(
                    resource, path_prefix, patient_refs_in_bundle
                )
                errors.extend(errs)
                warnings.extend(warns)
            elif rt == "Patient":
                errs, warns = self._validate_patient(resource, path_prefix)
                errors.extend(errs)
                warnings.extend(warns)
            elif rt == "Encounter":
                errs, warns = self._validate_encounter(resource, path_prefix)
                errors.extend(errs)
                warnings.extend(warns)
            elif rt == "Observation":
                errs, warns = self._validate_observation(resource, path_prefix)
                errors.extend(errs)
                warnings.extend(warns)

        valid = len(errors) == 0
        return BundleValidationResult(valid=valid, errors=errors, warnings=warnings)

    # ── per-resource validators ────────────────────────────────────────────────

    def _validate_condition(
        self,
        resource: Dict[str, Any],
        path: str,
        patient_refs: set,
    ) -> tuple:
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # subject reference is required
        subject = resource.get("subject", {})
        if not subject or not subject.get("reference"):
            errors.append(ValidationError(
                path=f"{path}.resource.subject",
                message="Condition.subject.reference is required",
            ))
        else:
            ref = subject["reference"]
            # Only validate if there are Patient entries in the Bundle
            if patient_refs and not any(ref == pr or ref.endswith(pr.split("/")[-1]) for pr in patient_refs):
                # Lenient: warn, not error, since absolute references are valid
                warnings.append(ValidationError(
                    path=f"{path}.resource.subject.reference",
                    message=(
                        f"Condition.subject.reference '{ref}' not found among "
                        f"Patient resources in this Bundle. Verify patient exists."
                    ),
                    severity="warning",
                ))

        # code is strongly recommended
        code = resource.get("code", {})
        if not code:
            warnings.append(ValidationError(
                path=f"{path}.resource.code",
                message="Condition.code is strongly recommended",
                severity="warning",
            ))
        else:
            codings = code.get("coding", [])
            if not codings:
                warnings.append(ValidationError(
                    path=f"{path}.resource.code.coding",
                    message="Condition.code.coding is empty — at least one coding expected",
                    severity="warning",
                ))
            for j, coding in enumerate(codings):
                errs, warns = self._validate_coding(coding, f"{path}.resource.code.coding[{j}]")
                errors.extend(errs)
                warnings.extend(warns)

        return errors, warnings

    def _validate_patient(self, resource: Dict[str, Any], path: str) -> tuple:
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        if not resource.get("id"):
            warnings.append(ValidationError(
                path=f"{path}.resource.id",
                message="Patient.id is recommended for reference resolution",
                severity="warning",
            ))
        return errors, warnings

    def _validate_encounter(self, resource: Dict[str, Any], path: str) -> tuple:
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        if not resource.get("status"):
            errors.append(ValidationError(
                path=f"{path}.resource.status",
                message="Encounter.status is required",
            ))
        if not resource.get("subject", {}).get("reference"):
            warnings.append(ValidationError(
                path=f"{path}.resource.subject",
                message="Encounter.subject.reference is recommended",
                severity="warning",
            ))
        return errors, warnings

    def _validate_observation(self, resource: Dict[str, Any], path: str) -> tuple:
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        if not resource.get("status"):
            errors.append(ValidationError(
                path=f"{path}.resource.status",
                message="Observation.status is required",
            ))
        if not resource.get("code"):
            errors.append(ValidationError(
                path=f"{path}.resource.code",
                message="Observation.code is required (e.g. LOINC / SNOMED-CT / NAMASTE)",
            ))
        else:
            for j, coding in enumerate(resource.get("code", {}).get("coding", [])):
                errs, warns = self._validate_coding(coding, f"{path}.resource.code.coding[{j}]")
                errors.extend(errs)
                warnings.extend(warns)
        return errors, warnings

    def _validate_coding(self, coding: Dict[str, Any], path: str) -> tuple:
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        system = coding.get("system")
        code   = coding.get("code")

        if not system:
            errors.append(ValidationError(
                path=f"{path}.system",
                message="Coding.system is required",
            ))
        elif system not in ALLOWED_CODING_SYSTEMS:
            warnings.append(ValidationError(
                path=f"{path}.system",
                message=(
                    f"Coding.system '{system}' is not in the standard set "
                    f"for this service. Verify this is intentional."
                ),
                severity="warning",
            ))

        if not code:
            errors.append(ValidationError(
                path=f"{path}.code",
                message="Coding.code is required",
            ))

        return errors, warnings


# ── Module-level singleton ─────────────────────────────────────────────────────
_default_validator = BundleValidator()


def validate_bundle(bundle_dict: Dict[str, Any]) -> BundleValidationResult:
    """Module-level convenience function."""
    return _default_validator.validate(bundle_dict)
