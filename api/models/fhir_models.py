"""FHIR R4 Pydantic models for inbound validation and serialization."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Coding(BaseModel):
    system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None
    version: Optional[str] = None


class CodeableConcept(BaseModel):
    coding: List[Coding] = Field(default_factory=list)
    text: Optional[str] = None


class Reference(BaseModel):
    reference: Optional[str] = None
    display: Optional[str] = None


class Condition(BaseModel):
    resourceType: str = "Condition"
    id: Optional[str] = None
    code: Optional[CodeableConcept] = None
    subject: Optional[Reference] = None
    clinicalStatus: Optional[CodeableConcept] = None
    verificationStatus: Optional[CodeableConcept] = None
    onsetDateTime: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    def get_primary_coding(self) -> Optional[Coding]:
        if self.code and self.code.coding:
            return self.code.coding[0]
        return None


class Encounter(BaseModel):
    resourceType: str = "Encounter"
    id: Optional[str] = None
    status: Optional[str] = None
    class_: Optional[Coding] = Field(None, alias="class")
    subject: Optional[Reference] = None
    meta: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True}


class BundleEntry(BaseModel):
    resource: Optional[Dict[str, Any]] = None
    fullUrl: Optional[str] = None
    request: Optional[Dict[str, Any]] = None


class FHIRBundle(BaseModel):
    """FHIR R4 Bundle — accepts Condition and Encounter resources."""
    resourceType: str = "Bundle"
    id: Optional[str] = None
    type: Optional[str] = None
    timestamp: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    entry: List[BundleEntry] = Field(default_factory=list)

    def get_conditions(self) -> List[Condition]:
        """Extract and validate Condition resources from entries."""
        conditions = []
        for entry in self.entry:
            if entry.resource and entry.resource.get("resourceType") == "Condition":
                conditions.append(Condition(**entry.resource))
        return conditions

    def get_encounters(self) -> List[Encounter]:
        encounters = []
        for entry in self.entry:
            if entry.resource and entry.resource.get("resourceType") == "Encounter":
                try:
                    encounters.append(Encounter(**entry.resource))
                except Exception:
                    pass
        return encounters

    def validate_structure(self) -> List[str]:
        """Return list of validation error messages. Empty = valid."""
        errors = []
        if self.resourceType != "Bundle":
            errors.append("resourceType must be 'Bundle'")
        if not self.entry:
            errors.append("Bundle must contain at least one entry")
        for i, entry in enumerate(self.entry):
            if entry.resource is None:
                errors.append(f"Entry {i} has no resource")
            elif "resourceType" not in entry.resource:
                errors.append(f"Entry {i} resource missing resourceType")
        return errors
