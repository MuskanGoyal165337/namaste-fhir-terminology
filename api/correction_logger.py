"""
Correction Logger
=================
Records code corrections when a practitioner overrides an AI-suggested code.
Append-only — original AI suggestions are never overwritten.

Stored fields:
  input_symptoms   : The query / symptom text that triggered the suggestion
  suggested_code   : AI-generated TM2/NAMASTE code
  corrected_code   : Practitioner's corrected code
  practitioner_id  : ABHA practitioner identifier
  timestamp        : UTC event time
  session_id       : Optional session correlation identifier

The correction is stored in the audit_logs table under event_type
"CORRECTION_SUBMITTED" to reuse the existing append-only infrastructure.
"""
from __future__ import annotations

import datetime
import logging
import uuid
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from security.audit_logger import AuditLogger, AuditEvent

logger = logging.getLogger("ayush_emr.api.correction_logger")


# ------------------------------------------------------------------ #
#  Correction payload                                                 #
# ------------------------------------------------------------------ #

class CorrectionPayload(BaseModel):
    input_symptoms: str
    suggested_code: Optional[str]
    corrected_code: str
    practitioner_id: str
    session_id: Optional[str] = None


# ------------------------------------------------------------------ #
#  Logger                                                             #
# ------------------------------------------------------------------ #

class CorrectionLogger:
    """
    Records practitioner corrections via the audit infrastructure.
    Corrections are appended to audit_logs with event_type='CORRECTION_SUBMITTED'.
    Original suggestions are preserved in the details blob — never overwritten.
    """

    def __init__(self) -> None:
        self._audit = AuditLogger()

    def log_correction(
        self,
        db: Session,
        payload: CorrectionPayload,
    ) -> str:
        """
        Persist a correction record.

        Returns the audit log row ID for traceability.
        """
        details = {
            "input_symptoms": payload.input_symptoms,
            "suggested_code": payload.suggested_code,     # original AI suggestion
            "corrected_code": payload.corrected_code,     # practitioner override
            "session_id": payload.session_id,
        }

        row = self._audit.log(
            db,
            AuditEvent(
                event_type="CORRECTION_SUBMITTED",
                actor_id=payload.practitioner_id,
                practitioner_id=payload.practitioner_id,
                action="correct",
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                details=details,
            ),
        )
        db.commit()
        logger.info(
            f"Correction logged: practitioner={payload.practitioner_id} "
            f"suggested={payload.suggested_code} -> corrected={payload.corrected_code}"
        )
        return row.id


def get_correction_logger() -> CorrectionLogger:
    """FastAPI dependency."""
    return CorrectionLogger()
