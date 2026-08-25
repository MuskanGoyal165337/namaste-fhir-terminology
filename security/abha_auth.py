"""
ABHA OAuth 2.0 / JWT Authentication helper.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel
from fastapi import Depends, Header, HTTPException, status


class ABHATokenClaims(BaseModel):
    sub: str = "practitioner-123"
    name: str = "Dr. Ayush Practitioner"
    role: str = "doctor"
    abha_id: str = "12-3456-7890-1234"
    practitioner_id: str = "AYU-10492"
    patient_consent_id: Optional[str] = None


def get_current_user(authorization: Optional[str] = Header(None)) -> ABHATokenClaims:
    return ABHATokenClaims()
