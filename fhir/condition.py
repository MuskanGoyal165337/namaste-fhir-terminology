"""
fhir/condition.py
==================
Double-coding service for FHIR R4 Condition resources.

SAFETY CONTRACT
---------------
* biomedicine_code is NEVER fabricated or inferred.
* If no validated biomedical mapping exists the biomedical Coding is omitted.
* The final code set is determined purely from authoritative DB-sourced data.
* Terminology version metadata is recorded for historical reproducibility.
"""
from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Optional

from api.models.fhir_models import CodeableConcept, Coding, Condition, Reference

# ── Canonical system URIs ──────────────────────────────────────────────────────
NAMASTE_SYSTEM = "http://namaste.ayush.gov.in"
TM2_SYSTEM     = "http://id.who.int/icd/release/11/mms"
BIO_SYSTEM     = "http://id.who.int/icd/release/11/mms/biomedical"

CLINICAL_STATUS_ACTIVE = CodeableConcept(
    coding=[Coding(
        system="http://terminology.hl7.org/CodeSystem/condition-clinical",
        code="active",
        display="Active",
    )]
)

VERIFICATION_STATUS_CONFIRMED = CodeableConcept(
    coding=[Coding(
        system="http://terminology.hl7.org/CodeSystem/condition-ver-status",
        code="confirmed",
        display="Confirmed",
    )]
)


@dataclass
class TraditionalDiagnosis:
    """
    Represents a single traditional medicine diagnosis with authoritative
    mapping information sourced from the terminology database.
    All mapping fields MUST come from the DB, not from AI suggestions.
    """
    # NAMASTE / Traditional concept
    source_term: str
    display: str
    namaste_system: str = NAMASTE_SYSTEM
    namaste_version: Optional[str] = None

    # ICD-11 TM2 mapping (null when no mapping exists)
    tm2_code: Optional[str] = None
    tm2_display: Optional[str] = None
    tm2_version: Optional[str] = None

    # ICD-11 Biomedicine — MUST be null unless supplied by authoritative source
    biomedicine_code: Optional[str] = None
    biomedicine_display: Optional[str] = None
    biomedicine_version: Optional[str] = None

    # Mapping provenance
    mapping_source: Optional[str] = None
    mapping_version: Optional[str] = None
    mapping_relationship: Optional[str] = None


@dataclass
class EncounterContext:
    """Patient / encounter information attached to a clinical condition."""
    patient_reference: str            # e.g. "Patient/12345"
    encounter_reference: Optional[str] = None
    onset_datetime: Optional[str] = None


class ConditionBuilder:
    """
    Builds a FHIR R4 Condition with double (or triple) coding.

    Resulting Condition.code will contain:
      1. NAMASTE coding            - always present (source of truth)
      2. ICD-11 TM2 coding         - present when tm2_code is not None
      3. ICD-11 Biomedicine coding - present ONLY when biomedicine_code is
                                     not None (authoritative source required)

    Meta.tag carries version provenance for reproducibility.
    """

    def build(
        self,
        diagnosis: TraditionalDiagnosis,
        context: EncounterContext,
        condition_id: Optional[str] = None,
        clinical_status: Optional[CodeableConcept] = None,
        verification_status: Optional[CodeableConcept] = None,
    ) -> Condition:
        """Construct and return a FHIR R4 Condition."""
        codings = self._build_codings(diagnosis)
        meta = self._build_meta(diagnosis)

        return Condition(
            resourceType="Condition",
            id=condition_id or str(uuid.uuid4()),
            meta=meta,
            clinicalStatus=clinical_status or CLINICAL_STATUS_ACTIVE,
            verificationStatus=verification_status or VERIFICATION_STATUS_CONFIRMED,
            code=CodeableConcept(coding=codings, text=diagnosis.display),
            subject=Reference(reference=context.patient_reference),
            onsetDateTime=context.onset_datetime,
        )

    @staticmethod
    def _build_codings(dx: TraditionalDiagnosis) -> list:
        """Build ordered coding list — only codings with non-null codes included."""
        codings = []

        # 1. NAMASTE - always present
        codings.append(Coding(
            system=dx.namaste_system,
            code=dx.source_term,
            display=dx.display,
            version=dx.namaste_version,
        ))

        # 2. ICD-11 TM2 - only when validated mapping exists
        if dx.tm2_code:
            codings.append(Coding(
                system=TM2_SYSTEM,
                code=dx.tm2_code,
                display=dx.tm2_display or dx.tm2_code,
                version=dx.tm2_version,
            ))

        # 3. ICD-11 Biomedicine - ONLY if authoritatively supplied; NEVER fabricated
        if dx.biomedicine_code:
            codings.append(Coding(
                system=BIO_SYSTEM,
                code=dx.biomedicine_code,
                display=dx.biomedicine_display or dx.biomedicine_code,
                version=dx.biomedicine_version,
            ))

        return codings

    @staticmethod
    def _build_meta(dx: TraditionalDiagnosis) -> dict:
        """Encode version/provenance into FHIR meta.tag for reproducibility."""
        tags = []

        if dx.namaste_version:
            tags.append({
                "system": "http://namaste.ayush.gov.in/meta/version",
                "code": dx.namaste_version,
                "display": f"NAMASTE version {dx.namaste_version}",
            })
        if dx.tm2_version:
            tags.append({
                "system": "http://id.who.int/icd/release/11/mms/meta/version",
                "code": dx.tm2_version,
                "display": f"ICD-11 TM2 version {dx.tm2_version}",
            })
        if dx.biomedicine_version:
            tags.append({
                "system": "http://id.who.int/icd/release/11/mms/biomedical/meta/version",
                "code": dx.biomedicine_version,
                "display": f"ICD-11 Biomedicine version {dx.biomedicine_version}",
            })
        if dx.mapping_source:
            tags.append({
                "system": "http://namaste.ayush.gov.in/meta/mapping-source",
                "code": dx.mapping_source,
                "display": f"Mapping source: {dx.mapping_source}",
            })
        if dx.mapping_version:
            tags.append({
                "system": "http://namaste.ayush.gov.in/meta/mapping-version",
                "code": dx.mapping_version,
                "display": f"Mapping version {dx.mapping_version}",
            })

        bio_tag = "available" if dx.biomedicine_code else "unavailable"
        tags.append({
            "system": "http://namaste.ayush.gov.in/meta/biomedical-mapping",
            "code": bio_tag,
            "display": f"Biomedical ICD-11 mapping: {bio_tag}",
        })

        meta = {"lastUpdated": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        if tags:
            meta["tag"] = tags
        return meta


_default_builder = ConditionBuilder()


def build_condition(
    diagnosis: TraditionalDiagnosis,
    context: EncounterContext,
    condition_id: Optional[str] = None,
) -> Condition:
    """Module-level convenience function using the default ConditionBuilder."""
    return _default_builder.build(diagnosis, context, condition_id)
