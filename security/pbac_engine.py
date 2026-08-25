"""
Policy-Based Access Control (PBAC) Engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from security.abha_auth import ABHATokenClaims


@dataclass
class PBACDecision:
    allowed: bool
    reason: str = ""


# Roles allowed to read aggregate analytics
_ANALYTICS_ROLES = {"doctor", "admin", "practitioner", "researcher"}


class PBACEngine:
    def check_permission(self, user: ABHATokenClaims, action: str, resource: str) -> bool:
        if user.role in ("doctor", "admin", "practitioner", "researcher"):
            return True
        return False

    def evaluate(self, role: str, resource: str, action: str) -> PBACDecision:
        """
        Evaluate whether a role is allowed to perform action on resource.
        Returns a PBACDecision with allowed=True/False and a reason string.
        """
        if resource == "AggregateData" and action == "read":
            if role in _ANALYTICS_ROLES:
                return PBACDecision(allowed=True, reason="Role has analytics read access.")
            return PBACDecision(
                allowed=False,
                reason=f"Role '{role}' is not permitted to read aggregate data.",
            )

        # Default: allow doctor/admin/practitioner for everything else
        if role in ("doctor", "admin", "practitioner"):
            return PBACDecision(allowed=True, reason="Default allow for clinical role.")

        return PBACDecision(allowed=False, reason=f"Role '{role}' is not authorized.")


def get_pbac_engine() -> PBACEngine:
    return PBACEngine()
