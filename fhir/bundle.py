"""
fhir/bundle.py
===============
Bundle construction service for the double-coding workflow.

Provides:
  build_double_coding_bundle(patient, encounter, conditions)
      -> FHIR R4 Bundle dict (transaction type)

The constructed Bundle contains:
  - Patient resource
  - Encounter resource (optional)
  - One or more Condition resources built by ConditionBuilder

The Bundle is suitable for POST /fhir/Bundle ingestion.
"""
from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, List, Optional

from api.models.fhir_models import Condition

FHIR_BUNDLE_VERSION = "4.0.1"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def build_double_coding_bundle(
    patient_id: str,
    conditions: List[Condition],
    encounter_id: Optional[str] = None,
    encounter_status: str = "finished",
    encounter_class_code: str = "AMB",
    encounter_class_display: str = "ambulatory",
    bundle_id: Optional[str] = None,
    bundle_type: str = "transaction",
) -> Dict[str, Any]:
    """
    Construct a FHIR R4 Bundle for a double-coding clinical encounter.

    Parameters
    ----------
    patient_id:
        Logical ID of the patient (used for Patient.id and references).
    conditions:
        List of FHIR Condition objects built by ConditionBuilder.
    encounter_id:
        Optional encounter logical ID.
    bundle_id:
        Optional bundle logical ID (UUID generated if omitted).
    bundle_type:
        FHIR bundle type — defaults to 'transaction'.

    Returns
    -------
    dict
        A FHIR R4 Bundle as a plain dict suitable for JSON serialisation.
    """
    bid = bundle_id or str(uuid.uuid4())
    eid = encounter_id or str(uuid.uuid4())
    patient_ref = f"Patient/{patient_id}"

    entries: List[Dict[str, Any]] = []

    # ── Patient entry ──────────────────────────────────────────────────────────
    entries.append({
        "fullUrl": patient_ref,
        "resource": {
            "resourceType": "Patient",
            "id": patient_id,
            "meta": {
                "lastUpdated": _now_iso(),
            },
        },
        "request": {
            "method": "PUT",
            "url": patient_ref,
        },
    })

    # ── Encounter entry ────────────────────────────────────────────────────────
    encounter_ref = f"Encounter/{eid}"
    entries.append({
        "fullUrl": encounter_ref,
        "resource": {
            "resourceType": "Encounter",
            "id": eid,
            "status": encounter_status,
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": encounter_class_code,
                "display": encounter_class_display,
            },
            "subject": {"reference": patient_ref},
            "meta": {"lastUpdated": _now_iso()},
        },
        "request": {
            "method": "PUT",
            "url": encounter_ref,
        },
    })

    # ── Condition entries ──────────────────────────────────────────────────────
    for cond in conditions:
        cond_id = cond.id or str(uuid.uuid4())
        cond_ref = f"Condition/{cond_id}"
        cond_dict = cond.model_dump(exclude_none=True)

        # Attach encounter reference if not already set
        if encounter_id and "encounter" not in cond_dict:
            cond_dict["encounter"] = {"reference": encounter_ref}

        entries.append({
            "fullUrl": cond_ref,
            "resource": cond_dict,
            "request": {
                "method": "PUT",
                "url": cond_ref,
            },
        })

    return {
        "resourceType": "Bundle",
        "id": bid,
        "meta": {
            "lastUpdated": _now_iso(),
            "tag": [{
                "system": "http://namaste.ayush.gov.in/meta/bundle-type",
                "code": "double-coding",
                "display": "AYUSH Double-Coding Clinical Bundle",
            }],
        },
        "type": bundle_type,
        "timestamp": _now_iso(),
        "entry": entries,
    }
