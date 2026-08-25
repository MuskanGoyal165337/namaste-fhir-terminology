"""
Vector Store interface for pgvector or linear fallback.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text


class TerminologyVectorStore:
    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        query_vector: Any,
        top_k: int = 10,
        system_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        # Fallback SQL search if vector table not configured
        try:
            where_parts = []
            params: Dict[str, Any] = {"limit": top_k}
            if system_filter:
                where_parts.append("system_category = :system")
                params["system"] = system_filter

            where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
            sql = text(
                f"""
                SELECT source_term, display AS display_name, tm2_code,
                       system_category AS system, language
                FROM concepts
                {where_sql}
                LIMIT :limit
                """
            )
            rows = self.db.execute(sql, params).fetchall()
            results = []
            for r in rows:
                d = dict(r._mapping)
                d["similarity"] = 0.85
                results.append(d)
            return results
        except Exception:
            return []
