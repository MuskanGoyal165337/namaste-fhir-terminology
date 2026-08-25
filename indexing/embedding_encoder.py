"""
BioBERT / Mock Embedding Encoder interface.
"""
from __future__ import annotations

from typing import List
import numpy as np


class BaseEncoder:
    def encode(self, texts: List[str]) -> np.ndarray:
        raise NotImplementedError


class MockEncoder(BaseEncoder):
    """Mock encoder returning deterministic float32 embeddings."""

    def encode(self, texts: List[str]) -> np.ndarray:
        rng = np.random.default_rng(42)
        return rng.standard_normal((len(texts), 768)).astype(np.float32)


def get_encoder(mock: bool = True) -> BaseEncoder:
    return MockEncoder()
