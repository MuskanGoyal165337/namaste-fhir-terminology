from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from api.config import get_settings

settings = get_settings()

import os
import json
from pathlib import Path

# Persistent SQLite fallback for local standalone execution when Postgres is absent
sqlite_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ayush_local.db"))

try:
    if settings.DATABASE_URL.startswith("postgresql"):
        engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            echo=False
        )
        # Test connection immediately
        with engine.connect() as conn:
            pass
    else:
        engine = create_engine(
            f"sqlite:///{sqlite_file}",
            connect_args={"check_same_thread": False}
        )
except Exception:
    engine = create_engine(
        f"sqlite:///{sqlite_file}",
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Ensure schema exists and seed essential concepts if empty."""
    if engine.url.drivername.startswith("postgresql"):
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception:
            pass
    from .base import Base
    from db.models import TerminologyConcept, DoctorPatientConnection, ClinicalHistoryItem
    Base.metadata.create_all(bind=engine)

    # Auto-seed if empty
    with SessionLocal() as db:
        if db.query(TerminologyConcept).count() == 0:
            processed_path = Path(__file__).parent.parent / "etl" / "data" / "processed" / "namaste_data_0440.json"
            if processed_path.exists():
                try:
                    with open(processed_path, "r", encoding="utf-8") as f:
                        records = json.load(f)
                    for r in records:
                        source_term = r.get("source_term") or r.get("term", "")
                        display_name = r.get("display_name") or r.get("english") or source_term
                        sys_cat = r.get("system", "Ayurveda")
                        tm2 = r.get("tm2_code")
                        c = TerminologyConcept(
                            source_term=source_term,
                            term=source_term,
                            display=display_name,
                            english=display_name,
                            system=sys_cat,
                            system_category=sys_cat,
                            source_version="2024-v1",
                            tm2_code=tm2,
                            tm2_display=r.get("tm2_display"),
                            language=r.get("language"),
                            code=r.get("code"),
                            mapping_status=r.get("mapping_status", "verified" if tm2 else "unmapped"),
                            mapping_relationship=r.get("mapping_relationship", "equivalent" if tm2 else "not-mapped"),
                            mapping_source="namaste_ingestor-v2",
                        )
                        db.add(c)
                    db.commit()
                except Exception:
                    pass

        # Seed initial Doctor-Patient Connections if empty
        if db.query(DoctorPatientConnection).count() == 0:
            seed_connections = [
                { "patient_id": "14-8829-1029-3381", "patient_name": "Rahul Verma", "patient_abha": "14-8829-1029-3381", "doctor_id": "AYU-10492", "doctor_name": "Dr. Rajesh Sharma", "system": "Ayurveda" },
                { "patient_id": "14-7731-2048-9921", "patient_name": "Ananya Iyer", "patient_abha": "14-7731-2048-9921", "doctor_id": "UNA-20183", "doctor_name": "Dr. Fatima Khan", "system": "Unani" },
                { "patient_id": "14-9082-3310-4417", "patient_name": "Mohan Das", "patient_abha": "14-9082-3310-4417", "doctor_id": "AYU-10492", "doctor_name": "Dr. Rajesh Sharma", "system": "Ayurveda" },
                { "patient_id": "14-5534-7790-2281", "patient_name": "Sunita Reddy", "patient_abha": "14-5534-7790-2281", "doctor_id": "SID-30741", "doctor_name": "Dr. Santhosh Kumar", "system": "Siddha" },
            ]
            for conn_item in seed_connections:
                db.add(DoctorPatientConnection(**conn_item))
            db.commit()

        # Seed initial Clinical History Items if empty
        if db.query(ClinicalHistoryItem).count() == 0:
            seed_history = [
                { "id": "h-001", "patient_id": "14-8829-1029-3381", "patient_name": "Rahul Verma", "patient_abha": "14-8829-1029-3381", "submitted_by": "Dr. Rajesh Sharma", "term": "hikkA (hidhmA)", "system": "Ayurveda", "tm2_code": "SM74(EA-2)", "icd_code": "MD12", "icd_display": "Cough", "added_date": "2026-08-10" },
                { "id": "h-002", "patient_id": "14-8829-1029-3381", "patient_name": "Rahul Verma", "patient_abha": "14-8829-1029-3381", "submitted_by": "Dr. Rajesh Sharma", "term": "jvaraH", "system": "Ayurveda", "tm2_code": "SP51(EC-3)", "icd_code": "MG26", "icd_display": "Fever of unknown origin", "added_date": "2026-08-12" },
                { "id": "h-003", "patient_id": "14-7731-2048-9921", "patient_name": "Ananya Iyer", "patient_abha": "14-7731-2048-9921", "submitted_by": "Dr. Fatima Khan", "term": "su-al", "system": "Unani", "tm2_code": "UE-01", "icd_code": "MD12", "icd_display": "Cough", "added_date": "2026-08-11" },
            ]
            for hist_item in seed_history:
                db.add(ClinicalHistoryItem(**hist_item))
            db.commit()


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for obtaining DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
