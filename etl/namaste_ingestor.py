"""
NAMASTE & AYUSH Terminology Ingestor
=====================================
Ingests raw CSV/JSON terminology datasets into the standardised schema without
modifying or fabricating source data.

Data integrity rules enforced here:
  - Original CSV fields (term, english, tm2_code, system) are preserved verbatim.
  - biomedicine_code is NEVER inferred or fabricated; it is always null unless
    explicitly present in the source file.
  - Mapping relationship labels follow the MappingRelationship controlled
    vocabulary.  Semantic similarity scores alone MUST NOT cause a record to
    be labelled 'equivalent' or 'exact'.
  - TM2 codes obtained directly from the source CSV are labelled 'equivalent'
    because they represent an authoritative cross-reference, not a model guess.
  - Missing TM2 codes result in mapping_status='unmapped' and
    mapping_relationship='not-mapped'.
"""

import datetime
import os
import json
import logging
from typing import Dict, List, Optional, Any

import pandas as pd
from sqlalchemy.orm import Session

from db.models import (
    TerminologyConcept,
    TerminologyMapping,
    MappingRelationship,
    MappingStatus,
)
from db.session import SessionLocal

logger = logging.getLogger("ayush_emr.etl.namaste_ingestor")

# ---------------------------------------------------------------------------
# Default column mapping: raw CSV column → internal canonical field name
# ---------------------------------------------------------------------------
DEFAULT_COLUMN_MAPPING = {
    "term": "source_term",        # raw 'term' → source_term (also stored as 'term')
    "english": "display_name",    # raw 'english' → display_name (also stored as 'english')
    "tm2_code": "tm2_code",
    "system": "system",
    "language": "language",
    "code": "code"
}

# Ingestor version string embedded in provenance metadata
INGESTOR_VERSION = "namaste_ingestor-v2"

# Required fields — at least one must be non-null for a record to be valid
_REQUIRED_ANY = ("source_term", "display_name")


# ---------------------------------------------------------------------------
# NamasteIngestor
# ---------------------------------------------------------------------------

class NamasteIngestor:
    """
    Ingestor for NAMASTE & AYUSH terminology CSV datasets.

    Maps raw CSV columns to the standardised schema while:
      - preserving original field values (term, english)
      - recording provenance (source, version, retrieved_at)
      - explicitly marking unmapped concepts (biomedicine_code=None,
        mapping_status='unmapped')
      - never fabricating codes or relationships
    """

    def __init__(self, column_mapping: Optional[Dict[str, str]] = None):
        self.column_mapping = column_mapping or DEFAULT_COLUMN_MAPPING

    # ------------------------------------------------------------------
    # 1. Read CSV
    # ------------------------------------------------------------------

    def read_csv(self, file_path: str, encoding: str = "utf-8") -> pd.DataFrame:
        """
        Reads raw CSV file, handling whitespace, Unicode, missing columns,
        and empty rows.  Returns a normalised DataFrame with canonical column
        names.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found: {file_path}")

        try:
            df = pd.read_csv(file_path, encoding=encoding, dtype=str)
        except UnicodeDecodeError:
            logger.warning(
                "UTF-8 decode failed for %s, falling back to latin-1", file_path
            )
            df = pd.read_csv(file_path, encoding="latin-1", dtype=str)

        # Drop entirely empty rows
        df = df.dropna(how="all")

        # Strip whitespace from column headers
        df.columns = [col.strip() for col in df.columns]

        # Apply configurable column mapping
        renamed_cols = {
            col: self.column_mapping[col]
            for col in df.columns
            if col in self.column_mapping
        }
        df = df.rename(columns=renamed_cols)

        # Ensure required canonical fields exist
        for col in ["source_term", "display_name"]:
            if col not in df.columns:
                df[col] = None

        for col, default in [
            ("system", "Ayurveda"),
            ("tm2_code", None),
            ("language", None),
            ("code", None),
        ]:
            if col not in df.columns:
                df[col] = default

        # Clean string values: strip whitespace, replace NaN/empty with None
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": None, "None": None, "NaN": None, "": None})

        # Drop rows where BOTH source_term and display_name are missing
        df = df.dropna(subset=["source_term", "display_name"], how="all")

        # Deduplicate
        df = df.drop_duplicates()

        return df

    # ------------------------------------------------------------------
    # 2. Validate individual record
    # ------------------------------------------------------------------

    def validate_record(self, rec: Dict[str, Any]) -> List[str]:
        """
        Returns a list of validation error messages.  Empty list means valid.

        Rules:
          - At least one of source_term or display_name must be non-null.
          - system must be non-null.
          - biomedicine_code must be None (never accepted from CSV ingestion
            because the current dataset does not contain biomedical codes and
            we must not fabricate them).
        """
        errors: List[str] = []
        if not rec.get("source_term") and not rec.get("display_name"):
            errors.append("Record must have source_term or display_name")
        if not rec.get("system"):
            errors.append("Record must have a system value")
        # Enforce the no-fabrication policy
        if rec.get("biomedicine_code") is not None:
            errors.append(
                "biomedicine_code MUST be null on ingest; "
                "ICD-11 Biomedicine codes must come from an authoritative external source"
            )
        return errors

    # ------------------------------------------------------------------
    # 3. Parse records from DataFrame
    # ------------------------------------------------------------------

    def _clean_val(self, val: Any) -> Optional[str]:
        if val is None:
            return None
        s = str(val).strip()
        if s in ("nan", "None", "NaN", ""):
            return None
        return s

    def parse_records(
        self,
        df: pd.DataFrame,
        source_version: Optional[str] = None,
        mapping_source: Optional[str] = None,
        source_system: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Converts a normalised DataFrame to a list of validated record dicts.

        Preserves original terminology.  Sets explicit provenance fields.
        biomedicine_code is always null; mapping_status reflects whether a
        TM2 code is present.

        Parameters
        ----------
        df : pd.DataFrame
            Output of read_csv().
        source_version : str, optional
            Version of the source terminology (e.g. "2024-v1").
        mapping_source : str, optional
            Provenance label for mappings (defaults to INGESTOR_VERSION).
        source_system : str, optional
            URI of the originating system.
        """
        _mapping_source = mapping_source or INGESTOR_VERSION
        retrieved_ts = datetime.datetime.now(datetime.timezone.utc)

        records: List[Dict[str, Any]] = []
        skipped = 0

        for _, row in df.iterrows():
            raw_term = self._clean_val(row.get("source_term"))
            raw_english = self._clean_val(row.get("display_name"))
            tm2_code = self._clean_val(row.get("tm2_code"))
            system = self._clean_val(row.get("system")) or "Ayurveda"

            rec: Dict[str, Any] = {
                # ── Original CSV fields preserved verbatim ──────────────────
                "term": raw_term,            # 'term' column from CSV
                "english": raw_english,      # 'english' column from CSV

                # ── Canonical internal fields ───────────────────────────────
                "source_term": raw_term,
                "display_name": raw_english,
                "tm2_code": tm2_code,
                "system": system,
                "language": self._clean_val(row.get("language")),
                "code": self._clean_val(row.get("code")),

                # ── Source provenance ───────────────────────────────────────
                "source_system": source_system,
                "source_code": self._clean_val(row.get("code")),
                "source_display": raw_english,
                "source_version": source_version,

                # ── WHO International Standard Terminology ──────────────────
                # Not populated at this stage (requires WHO IST API)
                "who_term_code": None,
                "who_term_display": None,

                # ── ICD-11 TM2 ─────────────────────────────────────────────
                "tm2_display": None,  # filled later if WHO TM2 API is called

                # ── ICD-11 Biomedicine (explicit null — never fabricated) ───
                "biomedicine_code": None,
                "biomedicine_display": None,

                # ── Mapping provenance ──────────────────────────────────────
                # TM2 codes from the source CSV are authoritative cross-references,
                # not AI inferences → labelled 'equivalent'.
                # Missing TM2 → 'not-mapped' / 'unmapped'.
                "mapping_relationship": (
                    MappingRelationship.EQUIVALENT if tm2_code
                    else MappingRelationship.NOT_MAPPED
                ),
                "mapping_status": (
                    MappingStatus.VERIFIED if tm2_code
                    else MappingStatus.UNMAPPED
                ),
                "mapping_source": _mapping_source,
                "mapping_version": source_version,
                "retrieved_at": retrieved_ts,
            }

            # Validate
            errors = self.validate_record(rec)
            if errors:
                logger.warning(
                    "Skipping invalid record (term=%r): %s", raw_term, "; ".join(errors)
                )
                skipped += 1
                continue

            records.append(rec)

        if skipped:
            logger.info("Skipped %d invalid records during parse_records.", skipped)

        return records

    # ------------------------------------------------------------------
    # 4. Export to JSON
    # ------------------------------------------------------------------

    def export_unified_json(
        self, records: List[Dict[str, Any]], output_path: str
    ) -> str:
        """
        Saves normalised records to namaste_data_0440.json.
        datetime values are serialised to ISO 8601 strings.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        def _serialise(obj: Any) -> Any:
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=4, ensure_ascii=False, default=_serialise)

        logger.info("Exported %d normalised records to %s", len(records), output_path)
        return output_path

    # ------------------------------------------------------------------
    # 5. Persist to database
    # ------------------------------------------------------------------

    def persist_to_db(
        self,
        records: List[Dict[str, Any]],
        db: Session,
        source_filename: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Persists normalised concepts and mappings to the database idempotently.

        On first encounter a concept is created; on subsequent runs only
        changed fields are updated (no duplicate rows are created).
        """
        created_concepts = 0
        updated_concepts = 0
        created_mappings = 0

        for rec in records:
            source_term = rec.get("source_term")
            system_name = rec.get("system") or "Ayurveda"
            display_name = rec.get("display_name") or source_term
            tm2_code = rec.get("tm2_code")
            code_val = rec.get("code")
            lang_val = rec.get("language")
            retrieved_ts = rec.get("retrieved_at")

            if not source_term and not display_name:
                continue

            # ── Idempotent lookup ────────────────────────────────────────
            query = db.query(TerminologyConcept).filter(
                TerminologyConcept.system == system_name
            )
            if source_term:
                query = query.filter(TerminologyConcept.source_term == source_term)
            else:
                query = query.filter(TerminologyConcept.display == display_name)

            concept = query.first()

            if concept:
                # Update only genuinely changed fields
                changed = False
                for attr, new_val in [
                    ("display", display_name),
                    ("tm2_code", tm2_code),
                    ("language", lang_val),
                    ("term", rec.get("term")),
                    ("english", rec.get("english")),
                    ("source_system", rec.get("source_system")),
                    ("source_code", rec.get("source_code")),
                    ("source_display", rec.get("source_display")),
                    ("source_version", rec.get("source_version")),
                    ("tm2_display", rec.get("tm2_display")),
                    # biomedicine_code: never updated from CSV ingestion
                    ("mapping_relationship", rec.get("mapping_relationship")),
                    ("mapping_status", rec.get("mapping_status")),
                    ("mapping_source", rec.get("mapping_source")),
                    ("mapping_version", rec.get("mapping_version")),
                ]:
                    if new_val is not None and getattr(concept, attr) != new_val:
                        setattr(concept, attr, new_val)
                        changed = True
                if changed:
                    updated_concepts += 1
            else:
                # Create new record
                concept = TerminologyConcept(
                    code=code_val,
                    source_term=source_term,
                    display=display_name,
                    system=system_name,
                    system_category=system_name,
                    tm2_code=tm2_code,
                    language=lang_val,
                    source_file=source_filename,
                    # Original CSV fields
                    term=rec.get("term"),
                    english=rec.get("english"),
                    # Source provenance
                    source_system=rec.get("source_system"),
                    source_code=rec.get("source_code"),
                    source_display=rec.get("source_display"),
                    source_version=rec.get("source_version"),
                    # WHO IST — not yet populated
                    who_term_code=None,
                    who_term_display=None,
                    # TM2 display — not yet populated (requires WHO TM2 API)
                    tm2_display=rec.get("tm2_display"),
                    # Biomedicine — ALWAYS null on CSV ingestion
                    biomedicine_code=None,
                    biomedicine_display=None,
                    # Mapping provenance
                    mapping_relationship=rec.get("mapping_relationship"),
                    mapping_status=rec.get("mapping_status"),
                    mapping_source=rec.get("mapping_source"),
                    mapping_version=rec.get("mapping_version"),
                    retrieved_at=retrieved_ts,
                )
                db.add(concept)
                db.flush()
                created_concepts += 1

            # ── TM2 mapping record ───────────────────────────────────────
            if tm2_code:
                # Idempotent lookup for TM2 target concept
                tm2_concept = db.query(TerminologyConcept).filter(
                    TerminologyConcept.system == "http://id.who.int/icd/release/11/mms",
                    TerminologyConcept.code == tm2_code,
                ).first()

                if not tm2_concept:
                    tm2_concept = TerminologyConcept(
                        code=tm2_code,
                        source_code=tm2_code,
                        display=f"ICD-11 TM2 Code {tm2_code}",
                        source_display=f"ICD-11 TM2 Code {tm2_code}",
                        system="http://id.who.int/icd/release/11/mms",
                        system_category="ICD-11-TM2",
                        tm2_code=tm2_code,
                        # Biomedicine null — TM2 ≠ biomedical ICD-11
                        biomedicine_code=None,
                        mapping_status=MappingStatus.VERIFIED,
                        mapping_source=rec.get("mapping_source"),
                        mapping_version=rec.get("mapping_version"),
                        retrieved_at=retrieved_ts,
                    )
                    db.add(tm2_concept)
                    db.flush()

                # Check if mapping already exists
                existing_mapping = db.query(TerminologyMapping).filter(
                    TerminologyMapping.source_concept_id == concept.id,
                    TerminologyMapping.target_concept_id == tm2_concept.id,
                ).first()

                if not existing_mapping:
                    mapping = TerminologyMapping(
                        source_concept_id=concept.id,
                        target_concept_id=tm2_concept.id,
                        # TM2 codes from source CSV are authoritative → equivalent
                        relationship_type=MappingRelationship.EQUIVALENT,
                        confidence_score=1.0,
                        mapping_status=MappingStatus.VERIFIED,
                        mapping_source=rec.get("mapping_source"),
                        mapping_version=rec.get("mapping_version"),
                        created_by="namaste_ingestor",
                    )
                    db.add(mapping)
                    created_mappings += 1

        db.commit()
        return {
            "created_concepts": created_concepts,
            "updated_concepts": updated_concepts,
            "created_mappings": created_mappings,
        }

    # ------------------------------------------------------------------
    # 6. Full pipeline
    # ------------------------------------------------------------------

    def process_file(
        self,
        file_path: str,
        output_json_path: str,
        db: Optional[Session] = None,
        source_version: Optional[str] = None,
        mapping_source: Optional[str] = None,
        source_system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Complete pipeline: Read CSV → Validate → Parse → Export JSON → Persist DB.

        Parameters
        ----------
        file_path : str
            Absolute path to the source CSV file.
        output_json_path : str
            Path where unified_terms.json will be written.
        db : Session, optional
            SQLAlchemy session.  If None, JSON export only.
        source_version : str, optional
            Terminology release version string for provenance.
        mapping_source : str, optional
            Provenance label for mappings.
        source_system : str, optional
            URI of the originating terminology system.
        """
        df = self.read_csv(file_path)
        records = self.parse_records(
            df,
            source_version=source_version,
            mapping_source=mapping_source,
            source_system=source_system,
        )
        self.export_unified_json(records, output_json_path)

        db_stats: Dict[str, int] = {}
        if db:
            db_stats = self.persist_to_db(
                records, db, source_filename=os.path.basename(file_path)
            )

        return {
            "total_records": len(records),
            "output_path": output_json_path,
            "db_stats": db_stats,
        }
