"""
GET /$expand — Cascading Hybrid Terminology Search
===================================================
Implements the three-tier cascade defined in the architecture:

  Tier 1 — Hash exact lookup (O(1), in-memory TerminologyHashIndex)
  Tier 2 — SQL ILIKE substring search (PostgreSQL / SQLite fallback)
  Tier 3 — BioBERT pgvector cosine similarity (semantic, with XAI)

Parameters
----------
q      : search query (required)
lang   : language filter (optional, e.g. "en", "sa")
system : system category filter (optional, e.g. "Ayurveda", "Siddha")
limit  : max results (default 10, max 50)

Response contract
-----------------
- source_term, display_name, tm2_code, system, language from actual data
- icd11_code: always null — the actual dataset does not include ICD-11 codes
  separate from TM2 codes; we do NOT fabricate them
- similarity: null for tier-1/2, float for tier-3
- match_method: "exact" | "substring" | "semantic"
- xai_weights: populated only for tier-3 results
"""
from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.session import get_db
from api.dependencies import get_hash_index, get_search_encoder
from api.models.response_models import ExpandResponse, ExpandResult, XAIWeight
from indexing.hash_index import TerminologyHashIndex
from indexing.embedding_encoder import BaseEncoder
from indexing.vector_store import TerminologyVectorStore
from indexing.xai_explainer import get_explainer

logger = logging.getLogger("ayush_emr.api.routes.expand")

router = APIRouter(tags=["Terminology"])

EMBEDDING_DIM = 768


# ------------------------------------------------------------------ #
#  Helper: convert raw record dict to ExpandResult                   #
# ------------------------------------------------------------------ #

def _to_result(
    rec: dict,
    match_method: str,
    similarity: Optional[float] = None,
    xai_weights: Optional[List[XAIWeight]] = None,
) -> ExpandResult:
    return ExpandResult(
        source_term=rec.get("source_term") or rec.get("display_name", ""),
        display_name=rec.get("display_name") or rec.get("source_term", ""),
        tm2_code=rec.get("tm2_code"),
        tm2_display=rec.get("tm2_display"),
        system=rec.get("system") or rec.get("system_category", ""),
        language=rec.get("language"),
        # Source provenance
        source_system=rec.get("source_system"),
        source_version=rec.get("source_version"),
        # WHO IST — null unless authoritatively mapped
        who_term_code=rec.get("who_term_code"),
        who_term_display=rec.get("who_term_display"),
        # Biomedicine — always null for current dataset; NEVER fabricated
        icd11_code=None,
        biomedicine_code=None,
        biomedicine_display=None,
        # Mapping metadata
        mapping_relationship=rec.get("mapping_relationship"),
        mapping_status=rec.get("mapping_status"),
        mapping_source=rec.get("mapping_source"),
        # Search metadata
        similarity=round(similarity, 4) if similarity is not None else None,
        match_method=match_method,
        xai_weights=xai_weights,
    )


# ------------------------------------------------------------------ #
#  Tier 2: SQL ILIKE substring search                                #
# ------------------------------------------------------------------ #

def _sql_substring_search(
    db: Session,
    query: str,
    system_filter: Optional[str],
    limit: int,
) -> List[dict]:
    """ILIKE search on concepts.source_term and concepts.display."""
    dialect = db.bind.dialect.name if db.bind else "sqlite"
    q = f"%{query.lower()}%"

    if dialect == "postgresql":
        like_op = "ILIKE"
        q_param = f"%{query}%"
    else:
        like_op = "LIKE"
        q_param = q  # SQLite LIKE is case-insensitive by default for ASCII

    where_parts = [
        f"(LOWER(c.source_term) {like_op} :q OR LOWER(c.display) {like_op} :q)"
    ]
    params: dict = {"q": q_param, "limit": limit}

    if system_filter:
        where_parts.append("c.system_category = :system")
        params["system"] = system_filter

    where_sql = " AND ".join(where_parts)
    sql = text(
        f"""
        SELECT c.source_term, c.display AS display_name, c.tm2_code,
               c.system_category AS system, c.language
        FROM concepts c
        WHERE {where_sql}
        LIMIT :limit
        """
    )
    rows = db.execute(sql, params).fetchall()
    return [dict(r._mapping) for r in rows]


# ------------------------------------------------------------------ #
#  Tier 3: BioBERT + pgvector cosine similarity                      #
# ------------------------------------------------------------------ #

def _semantic_search(
    db: Session,
    query: str,
    encoder: BaseEncoder,
    system_filter: Optional[str],
    limit: int,
) -> List[dict]:
    """Encode query and search concept_embeddings via pgvector / linear fallback."""
    q_vec = encoder.encode([query])[0]  # (768,)
    store = TerminologyVectorStore(db)
    return store.search(q_vec, top_k=limit, system_filter=system_filter)


# ------------------------------------------------------------------ #
#  Route                                                              #
# ------------------------------------------------------------------ #

@router.get("/$expand", response_model=ExpandResponse)
def expand(
    q: str = Query(..., min_length=1, description="Search query"),
    lang: Optional[str] = Query(None, description="Language filter (e.g. 'en', 'sa')"),
    system: Optional[str] = Query(None, description="System category filter"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db: Session = Depends(get_db),
    hash_index: TerminologyHashIndex = Depends(get_hash_index),
    encoder: BaseEncoder = Depends(get_search_encoder),
):
    """
    Three-tier cascading terminology expansion:
      1. Hash exact lookup
      2. SQL ILIKE substring search
      3. BioBERT semantic search (with XAI weights)
    """
    results: List[ExpandResult] = []
    used_method = "exact"

    # ── Tier 1: Hash exact lookup ──────────────────────────────────
    exact_hits = hash_index.lookup_source_term(q)
    if not exact_hits:
        exact_hits = hash_index.lookup_display(q)

    if exact_hits:
        for rec in exact_hits[:limit]:
            if system and rec.get("system") != system:
                continue
            if lang and rec.get("language") and rec["language"] != lang:
                continue
            results.append(_to_result(rec, "exact"))
        used_method = "exact"

    # ── Tier 2: SQL ILIKE substring (if exact returned nothing) ────
    if not results:
        used_method = "substring"
        sql_hits = _sql_substring_search(db, q, system, limit)
        for row in sql_hits:
            results.append(_to_result(row, "substring"))

    # ── Tier 3: BioBERT semantic (if tiers 1+2 both empty) ────────
    if not results:
        used_method = "semantic"
        try:
            sem_hits = _semantic_search(db, q, encoder, system, limit)
        except Exception as exc:
            logger.warning(f"Semantic search failed: {exc}")
            sem_hits = []

        explainer = get_explainer(mock=True)  # mock in all envs for now
        for hit in sem_hits:
            xai = None
            try:
                explanation = explainer.explain(q, hit.get("display_name") or hit.get("source_term", ""))
                xai = [XAIWeight(token=t, score=s) for t, s in explanation.token_scores]
            except Exception:
                pass
            results.append(_to_result(hit, "semantic", similarity=hit.get("similarity"), xai_weights=xai))

    return ExpandResponse(
        query=q,
        lang=lang,
        system_filter=system,
        total=len(results),
        results=results,
    )
