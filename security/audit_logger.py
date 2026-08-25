"""
Audit logger infrastructure for capturing append-only security and correction events.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from db.models import AuditLog

logger = logging.getLogger("ayush_emr.security.audit_logger")


class AuditEvent:
    def __init__(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        practitioner_id: Optional[str] = None,
        patient_consent_id: Optional[str] = None,
        action: Optional[str] = None,
        client_ip: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.event_type = event_type
        self.user_id = user_id or actor_id or practitioner_id
        self.actor_id = actor_id
        self.practitioner_id = practitioner_id
        self.patient_consent_id = patient_consent_id
        self.action = action
        self.client_ip = client_ip
        self.details = details or {}
        self.timestamp = timestamp or datetime.now(timezone.utc)


class AuditLogger:
    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def log(self, db: Optional[Session] = None, event: Optional[AuditEvent] = None) -> Optional[AuditLog]:
        target_db = db or self.db
        if not target_db or not event:
            return None
        try:
            log_entry = AuditLog(
                event_type=event.event_type,
                actor_id=event.user_id,
                details=event.details,
                ip_address=event.client_ip,
            )
            target_db.add(log_entry)
            target_db.flush()
            return log_entry
        except Exception as exc:
            logger.error(f"Failed to record audit log: {exc}")
            return None

    def log_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
    ) -> Optional[AuditLog]:
        target_db = db or self.db
        if not target_db:
            logger.info(f"[AUDIT] {event_type} | User: {user_id} | Resource: {resource} | Action: {action}")
            return None

        try:
            log_entry = AuditLog(
                event_type=event_type,
                actor_id=user_id,
                details=details or {},
            )
            target_db.add(log_entry)
            target_db.flush()
            return log_entry
        except Exception as exc:
            logger.error(f"Failed to record audit log: {exc}")
            return None


def get_audit_logger() -> AuditLogger:
    return AuditLogger()

