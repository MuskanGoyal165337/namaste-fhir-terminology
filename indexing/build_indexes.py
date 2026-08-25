"""
Factory function to build TerminologyHashIndex from processed namaste_data_0440.json.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from indexing.hash_index import TerminologyHashIndex


def build_hash_index(json_path: Optional[Path] = None) -> TerminologyHashIndex:
    """Build and return TerminologyHashIndex singleton instance."""
    return TerminologyHashIndex(data_path=json_path)
