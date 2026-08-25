"""
Application-level dependencies and shared singleton state.

Manages the hash index and encoder singletons so they are loaded once
at startup and reused across all requests — avoids reloading per request.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from indexing.hash_index import TerminologyHashIndex
from indexing.build_indexes import build_hash_index
from indexing.embedding_encoder import BaseEncoder, get_encoder

logger = logging.getLogger("ayush_emr.api.dependencies")

# ------------------------------------------------------------------ #
#  Application State                                                  #
# ------------------------------------------------------------------ #

class AppState:
    """Holds the singleton instances shared across the application lifetime."""

    def __init__(self) -> None:
        self._hash_index: Optional[TerminologyHashIndex] = None
        self._encoder: Optional[BaseEncoder] = None

    def init_hash_index(self, mock: bool = False) -> TerminologyHashIndex:
        """Build or rebuild hash index from namaste_data_0440.json."""
        self._hash_index = build_hash_index()
        logger.info(f"Hash index initialised: {len(self._hash_index)} records.")
        return self._hash_index

    def init_encoder(self, mock: bool = False) -> BaseEncoder:
        """Load the BioBERT encoder (or mock)."""
        self._encoder = get_encoder(mock=mock)
        logger.info(f"Encoder initialised: {type(self._encoder).__name__}")
        return self._encoder

    @property
    def hash_index(self) -> Optional[TerminologyHashIndex]:
        return self._hash_index

    @property
    def encoder(self) -> Optional[BaseEncoder]:
        return self._encoder


# Singleton application state
_app_state: AppState = AppState()


def get_app_state() -> AppState:
    return _app_state


# ------------------------------------------------------------------ #
#  FastAPI Dependencies                                               #
# ------------------------------------------------------------------ #

def get_hash_index() -> TerminologyHashIndex:
    """
    FastAPI dependency. Returns the shared hash index.
    If not yet initialised (e.g., startup failed), builds it on demand.
    """
    state = _app_state
    if state.hash_index is None:
        logger.warning("Hash index not initialised at startup; building on demand.")
        state.init_hash_index()
    return state.hash_index


def get_search_encoder() -> BaseEncoder:
    """
    FastAPI dependency. Returns the shared BioBERT encoder.
    Falls back to mock encoder if not initialised.
    """
    state = _app_state
    if state.encoder is None:
        logger.warning("Encoder not initialised; using mock encoder.")
        state.init_encoder(mock=True)
    return state.encoder
