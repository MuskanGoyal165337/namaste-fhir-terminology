"""
XAI Explainer for model interpretability weights.
"""
from __future__ import annotations

from typing import List, Tuple


class XAIExplanation:
    def __init__(self, token_scores: List[Tuple[str, float]]):
        self.token_scores = token_scores


class XAIExplainer:
    def explain(self, query: str, target: str) -> XAIExplanation:
        tokens = query.split()
        if not tokens:
            return XAIExplanation([])
        score = round(1.0 / len(tokens), 4)
        return XAIExplanation([(t, score) for t in tokens])


def get_explainer(mock: bool = True) -> XAIExplainer:
    return XAIExplainer()
