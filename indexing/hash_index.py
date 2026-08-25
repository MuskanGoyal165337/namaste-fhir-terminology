"""
Fast in-memory O(1) hash index for exact terminology lookups.
Indexed by source_term, display_name, tm2_code, and code.
Uses processed namaste_data_0440.json dataset.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("ayush_emr.indexing.hash_index")

DEFAULT_PROCESSED_PATH = (
    Path(__file__).parent.parent / "etl" / "data" / "processed" / "namaste_data_0440.json"
)


class TerminologyHashIndex:
    """In-memory hash index for exact O(1) lookup on concepts."""

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = Path(data_path) if data_path else DEFAULT_PROCESSED_PATH
        self._source_term_index: Dict[str, List[Dict[str, Any]]] = {}
        self._display_index: Dict[str, List[Dict[str, Any]]] = {}
        self._tm2_index: Dict[str, List[Dict[str, Any]]] = {}
        self._records: List[Dict[str, Any]] = []
        self.load_index()

    def load_index(self) -> None:
        """Load concepts from JSON and build hash maps."""
        self._source_term_index.clear()
        self._display_index.clear()
        self._tm2_index.clear()
        self._records.clear()

        if not self.data_path.exists():
            logger.warning(f"Data file not found at {self.data_path}")
            return

        with open(self.data_path, "r", encoding="utf-8") as f:
            raw_records = json.load(f)

        for r in raw_records:
            source_term = r.get("source_term") or r.get("term")
            display_name = r.get("display_name") or r.get("english") or source_term
            tm2_code = r.get("tm2_code")
            system_val = r.get("system", "Ayurveda")

            rec: Dict[str, Any] = {
                "source_term": source_term,
                "display_name": display_name,
                "term": source_term,
                "english": display_name,
                "tm2_code": tm2_code,
                "tm2_display": r.get("tm2_display"),
                "system": system_val,
                "system_category": system_val,
                "language": r.get("language"),
                "code": r.get("code"),
                "source_system": r.get("source_system"),
                "source_version": r.get("source_version", "2024-v1"),
                "who_term_code": r.get("who_term_code"),
                "who_term_display": r.get("who_term_display"),
                "mapping_relationship": r.get(
                    "mapping_relationship", "equivalent" if tm2_code else "not-mapped"
                ),
                "mapping_status": r.get(
                    "mapping_status", "verified" if tm2_code else "unmapped"
                ),
                "mapping_source": r.get("mapping_source", "namaste_ingestor-v2"),
            }
            self._records.append(rec)

            if source_term:
                key = str(source_term).strip().lower()
                self._source_term_index.setdefault(key, []).append(rec)

            if display_name:
                key = str(display_name).strip().lower()
                self._display_index.setdefault(key, []).append(rec)

            if tm2_code:
                key = str(tm2_code).strip().lower()
                self._tm2_index.setdefault(key, []).append(rec)

        logger.info(f"Loaded {len(self._records)} records into TerminologyHashIndex.")

    def lookup_source_term(self, term: str) -> List[Dict[str, Any]]:
        if not term:
            return []
        return self._source_term_index.get(term.strip().lower(), [])

    def lookup_display(self, display: str) -> List[Dict[str, Any]]:
        if not display:
            return []
        return self._display_index.get(display.strip().lower(), [])

    def lookup_tm2(self, code: str) -> List[Dict[str, Any]]:
        if not code:
            return []
        return self._tm2_index.get(code.strip().lower(), [])

    def get(self, query: str) -> Optional[Dict[str, Any]]:
        if not query:
            return None
        q_norm = query.strip().lower()
        res = self.lookup_source_term(q_norm) or self.lookup_display(q_norm) or self.lookup_tm2(q_norm)
        return res[0] if res else None

    def __len__(self) -> int:
        return len(self._records)
