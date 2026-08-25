from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Dict, Any
from db.session import get_db
from api.config import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()

class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    version: str
    database: Dict[str, Any]

@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint testing service status and DB connection."""
    db_status = "connected"
    db_message = "Database connection successful"
    pgvector_installed = False

    try:
        # Test basic query
        db.execute(text("SELECT 1"))
        
        # Check pgvector extension if postgres
        if db.bind.dialect.name == "postgresql":
            result = db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchone()
            if result:
                pgvector_installed = True
    except Exception as e:
        db_status = "error"
        db_message = str(e)

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        version=settings.VERSION,
        database={
            "status": db_status,
            "message": db_message,
            "pgvector_extension": pgvector_installed,
            "engine": db.bind.dialect.name if db.bind else "unknown"
        }
    )
