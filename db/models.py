import uuid
import datetime
from typing import Optional, Any
from sqlalchemy import (
    String, Text, Float, Boolean, Integer, JSON, ForeignKey, DateTime, Index
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy import JSON as Vector
from .base import Base, TimestampMixin


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Controlled vocabulary constants
# ---------------------------------------------------------------------------

class MappingRelationship:
    """
    Controlled vocabulary for concept mapping relationships.

    Semantics follow FHIR ConceptMap equivalence codes:
      exact        — The concepts are exactly the same (same code, same system).
      equivalent   — The concepts are semantically equivalent.
      broader      — The source concept is broader than the target.
      narrower     — The source concept is narrower than the target.
      related      — There is some relationship but not equivalence.
      not-mapped   — No mapping exists (explicit absence, not unknown).
      not-applicable — Mapping is not applicable for this concept.

    IMPORTANT: semantic similarity scores alone MUST NOT be used to infer
    equivalence.  Only authoritative human-reviewed or source-provided
    mappings may be labelled 'exact' or 'equivalent'.
    """
    EXACT = "exact"
    EQUIVALENT = "equivalent"
    BROADER = "broader"
    NARROWER = "narrower"
    RELATED = "related"
    NOT_MAPPED = "not-mapped"
    NOT_APPLICABLE = "not-applicable"

    ALL = {EXACT, EQUIVALENT, BROADER, NARROWER, RELATED, NOT_MAPPED, NOT_APPLICABLE}


class MappingStatus:
    """Lifecycle status for a terminology mapping."""
    VERIFIED = "verified"        # Human-reviewed and confirmed.
    CANDIDATE = "candidate"      # System-generated, awaiting review.
    UNMAPPED = "unmapped"        # No mapping available.
    REJECTED = "rejected"        # Reviewed and rejected.

    ALL = {VERIFIED, CANDIDATE, UNMAPPED, REJECTED}


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------

class TerminologyConcept(Base, TimestampMixin):
    """
    Stores standardised clinical concepts (NAMASTE, ICD-11-TM2, WHO IST, Biomedicine).

    Original CSV field names ('term', 'english', 'tm2_code', 'system') are
    preserved verbatim alongside their canonical counterparts so no source
    data is silently lost during ingestion.

    Biomedicine fields are explicitly nullable: biomedicine_code MUST remain
    null unless supplied by an authoritative external source.  It is NEVER
    inferred or fabricated.
    """
    __tablename__ = "concepts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # ── Canonical / legacy fields (kept for backward compatibility) ──────────
    code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    source_term: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)
    system: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    system_category: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="Ayurveda, Siddha, Unani, Homeopathy, Yoga, ICD-11-TM2, SNOMED-CT"
    )
    definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tm2_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ── Original CSV field names preserved verbatim ──────────────────────────
    term: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, index=True,
        comment="Original 'term' column from source CSV (NAMASTE transliterated form)"
    )
    english: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True,
        comment="Original 'english' column from source CSV (English translation)"
    )

    # ── Source system provenance ─────────────────────────────────────────────
    source_system: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True,
        comment="Originating system URI e.g. http://namaste.ayush.gov.in"
    )
    source_code: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="Code in the originating system (mirrors 'code' when available)"
    )
    source_display: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True,
        comment="Display name in the originating system"
    )
    source_version: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Release/version of the originating terminology"
    )

    # ── WHO International Standard Terminology ───────────────────────────────
    # Populated only when an authoritative WHO IST mapping is available.
    who_term_code: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="WHO International Standard Terminology code — null unless authoritatively mapped"
    )
    who_term_display: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True,
        comment="WHO International Standard Terminology display name"
    )

    # ── ICD-11 TM2 (Traditional Medicine Module 2) ───────────────────────────
    tm2_display: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True,
        comment="Human-readable display for tm2_code (e.g. 'Cough in Traditional Medicine')"
    )

    # ── ICD-11 Biomedicine ───────────────────────────────────────────────────
    # POLICY: biomedicine_code MUST remain null unless an authoritative external
    # system (e.g. WHO ICD-11 MMS API) supplies it explicitly.
    # It MUST NOT be inferred from semantic similarity or AI models.
    biomedicine_code: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="ICD-11 Biomedicine code — NEVER fabricated; null unless explicitly supplied"
    )
    biomedicine_display: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True,
        comment="ICD-11 Biomedicine code display name"
    )

    # ── Mapping provenance ───────────────────────────────────────────────────
    mapping_relationship: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment=(
            "Mapping relationship type: "
            "exact | equivalent | broader | narrower | related | not-mapped | not-applicable"
        )
    )
    mapping_status: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Mapping lifecycle: verified | candidate | unmapped | rejected"
    )
    mapping_source: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="Provenance: who/what created this mapping (e.g. 'namaste_ingestor-v1')"
    )
    mapping_version: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Version identifier for the mapping ruleset"
    )
    retrieved_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="UTC timestamp when this concept was first retrieved from the source"
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    source_mappings = relationship(
        "TerminologyMapping",
        foreign_keys="TerminologyMapping.source_concept_id",
        back_populates="source_concept",
        cascade="all, delete-orphan"
    )
    target_mappings = relationship(
        "TerminologyMapping",
        foreign_keys="TerminologyMapping.target_concept_id",
        back_populates="target_concept",
        cascade="all, delete-orphan"
    )
    embedding_record = relationship(
        "ConceptEmbedding",
        back_populates="concept",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_concept_source_system", "source_term", "system"),
    )


class TerminologyMapping(Base, TimestampMixin):
    """
    Maps AYUSH concepts to international standards (e.g. NAMASTE → ICD-11-TM2).

    relationship_type follows the MappingRelationship controlled vocabulary.
    Semantic similarity scores MUST NOT be used to infer 'equivalent' or 'exact'
    relationships without human review.
    """
    __tablename__ = "terminology_mappings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    source_concept_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_concept_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default=MappingRelationship.RELATED,
        comment=(
            "Controlled vocabulary: "
            "exact | equivalent | broader | narrower | related | not-mapped | not-applicable"
        )
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    mapping_status: Mapped[str] = mapped_column(
        String(50), default=MappingStatus.CANDIDATE, nullable=False,
        comment="verified | candidate | unmapped | rejected"
    )
    mapping_source: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="Provenance: who/what created this mapping (e.g. 'namaste_ingestor-v1')"
    )
    mapping_version: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Version identifier for the mapping ruleset used"
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    source_concept = relationship(
        "TerminologyConcept", foreign_keys=[source_concept_id], back_populates="source_mappings"
    )
    target_concept = relationship(
        "TerminologyConcept", foreign_keys=[target_concept_id], back_populates="target_mappings"
    )
    corrections = relationship(
        "CorrectionLog", back_populates="mapping", cascade="all, delete-orphan"
    )


class ConceptEmbedding(Base):
    """
    Stores pgvector 768-dimensional BioBERT dense vector embeddings for semantic search.
    HNSW index should be created in PostgreSQL via:
      CREATE INDEX ON concept_embeddings USING hnsw (embedding vector_cosine_ops);
    """
    __tablename__ = "concept_embeddings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    concept_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("concepts.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # 768 dimensions — BioBERT (dmis-lab/biobert-v1.1) output. Fallback to JSON on SQLite.
    embedding = mapped_column(Vector(768).with_variant(JSON, "sqlite"), nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), default="dmis-lab/biobert-v1.1", nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False
    )

    # Relationship
    concept = relationship("TerminologyConcept", back_populates="embedding_record")


class FHIRBundle(Base, TimestampMixin):
    """Stores incoming raw and transformed AYUSH FHIR clinical encounters/bundles."""
    __tablename__ = "fhir_bundles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    bundle_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    patient_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    encounter_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    transformed_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False,
        comment="pending, processed, failed, validated"
    )


class AuditLog(Base):
    """Audit trails for system events, queries, security, and rule enforcement."""
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )


class CorrectionLog(Base, TimestampMixin):
    """Logs human clinician corrections and feedback for mapping refine pipelines."""
    __tablename__ = "correction_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    mapping_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("terminology_mappings.id", ondelete="CASCADE"), nullable=False
    )
    suggested_target_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("concepts.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False,
        comment="pending, approved, rejected"
    )
    submitted_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    mapping = relationship("TerminologyMapping", back_populates="corrections")
    suggested_target = relationship("TerminologyConcept", foreign_keys=[suggested_target_id])


class NHCXRule(Base, TimestampMixin):
    """Stores National Health Claims Exchange validation rules and constraints."""
    __tablename__ = "nhcx_rules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    rule_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    validation_expression: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CodeSystemVersion(Base, TimestampMixin):
    """Metadata tracking versions of installed terminology systems (NAMASTE, ICD, etc)."""
    __tablename__ = "code_system_versions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    system_uri: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    release_date: Mapped[Optional[datetime.date]] = mapped_column(nullable=True)
    concept_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("idx_system_uri_version", "system_uri", "version", unique=True),
    )


class ClinicalCondition(Base, TimestampMixin):
    """
    Stores double-coded clinical condition records with version provenance
    for historical reproducibility.
    """
    __tablename__ = "clinical_conditions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    condition_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    encounter_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    bundle_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Traditional concept
    source_term: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    display: Mapped[str] = mapped_column(String(500), nullable=False)
    namaste_system: Mapped[str] = mapped_column(
        String(255), default="http://namaste.ayush.gov.in", nullable=False
    )
    namaste_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # ICD-11 TM2 mapping
    tm2_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    tm2_display: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tm2_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # ICD-11 Biomedicine mapping (NEVER fabricated)
    biomedicine_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    biomedicine_display: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    biomedicine_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Mapping metadata & provenance
    mapping_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mapping_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mapping_relationship: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Clinical status
    clinical_status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), default="confirmed", nullable=False)
    onset_datetime: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Full FHIR Condition payload JSON
    fhir_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class DoctorPatientConnection(Base, TimestampMixin):
    """Stores persistent doctor-patient assignments and connections in the database."""
    __tablename__ = "doctor_patient_connections"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    patient_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    patient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    patient_abha: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    doctor_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    doctor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    system: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class ClinicalHistoryItem(Base, TimestampMixin):
    """Stores permanent clinical history entries for patients in the database."""
    __tablename__ = "clinical_history_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    patient_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    patient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    patient_abha: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    submitted_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    term: Mapped[str] = mapped_column(String(500), nullable=False)
    system: Mapped[str] = mapped_column(String(100), nullable=False)
    tm2_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    icd_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    icd_display: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    added_date: Mapped[str] = mapped_column(String(50), nullable=False)

