"""
api/routes/history.py
=====================
Persistent database endpoints for Patient Clinical History and Doctor-Patient Connections.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import ClinicalHistoryItem, DoctorPatientConnection

router = APIRouter(prefix="", tags=["Clinical History & Connections"])


# ── Pydantic Schemas ─────────────────────────────────────────────────────────

class ClinicalHistoryItemSchema(BaseModel):
    id: Optional[str] = None
    patientId: str
    patientName: Optional[str] = None
    patientAbha: Optional[str] = None
    submittedBy: Optional[str] = None
    term: str
    system: str
    tm2Code: Optional[str] = None
    icdCode: Optional[str] = None
    icdDisplay: Optional[str] = None
    addedDate: Optional[str] = None

class ConnectionSchema(BaseModel):
    patientId: str
    patientName: Optional[str] = None
    patientAbha: Optional[str] = None
    doctorId: Optional[str] = None
    doctorName: Optional[str] = None
    system: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/history", response_model=List[ClinicalHistoryItemSchema])
def get_all_history(db: Session = Depends(get_db)):
    """Fetch all stored clinical history records from the database."""
    items = db.query(ClinicalHistoryItem).order_by(ClinicalHistoryItem.created_at.desc()).all()
    return [
        ClinicalHistoryItemSchema(
            id=item.id,
            patientId=item.patient_id,
            patientName=item.patient_name,
            patientAbha=item.patient_abha,
            submittedBy=item.submitted_by,
            term=item.term,
            system=item.system,
            tm2Code=item.tm2_code,
            icdCode=item.icd_code,
            icdDisplay=item.icd_display,
            addedDate=item.added_date,
        )
        for item in items
    ]


@router.post("/history", response_model=ClinicalHistoryItemSchema, status_code=status.HTTP_201_CREATED)
def add_history_item(payload: ClinicalHistoryItemSchema, db: Session = Depends(get_db)):
    """Persist a new clinical history item permanently in the database."""
    item_id = payload.id or f"h-{int(db.query(ClinicalHistoryItem).count() + 100)}"
    db_item = ClinicalHistoryItem(
        id=item_id,
        patient_id=payload.patientId,
        patient_name=payload.patientName,
        patient_abha=payload.patientAbha,
        submitted_by=payload.submittedBy,
        term=payload.term,
        system=payload.system,
        tm2_code=payload.tm2Code,
        icd_code=payload.icdCode,
        icd_display=payload.icdDisplay,
        added_date=payload.addedDate or "2026-08-15",
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return ClinicalHistoryItemSchema(
        id=db_item.id,
        patientId=db_item.patient_id,
        patientName=db_item.patient_name,
        patientAbha=db_item.patient_abha,
        submittedBy=db_item.submitted_by,
        term=db_item.term,
        system=db_item.system,
        tm2Code=db_item.tm2_code,
        icdCode=db_item.icd_code,
        icdDisplay=db_item.icd_display,
        addedDate=db_item.added_date,
    )


@router.get("/connections", response_model=List[ConnectionSchema])
def get_all_connections(db: Session = Depends(get_db)):
    """Fetch all doctor-patient connections from the database."""
    conns = db.query(DoctorPatientConnection).all()
    return [
        ConnectionSchema(
            patientId=c.patient_id,
            patientName=c.patient_name,
            patientAbha=c.patient_abha,
            doctorId=c.doctor_id,
            doctorName=c.doctor_name,
            system=c.system,
        )
        for c in conns
    ]


@router.post("/connections", response_model=ConnectionSchema)
def save_connection(payload: ConnectionSchema, db: Session = Depends(get_db)):
    """Create or update a doctor-patient connection permanently in the database."""
    conn = db.query(DoctorPatientConnection).filter(
        DoctorPatientConnection.patient_id == payload.patientId
    ).first()

    if not conn:
        conn = DoctorPatientConnection(
            patient_id=payload.patientId,
            patient_name=payload.patientName,
            patient_abha=payload.patientAbha,
            doctor_id=payload.doctorId,
            doctor_name=payload.doctorName,
            system=payload.system,
        )
        db.add(conn)
    else:
        conn.doctor_id = payload.doctorId
        conn.doctor_name = payload.doctorName
        if payload.patientName:
            conn.patient_name = payload.patientName
        if payload.patientAbha:
            conn.patient_abha = payload.patientAbha
        if payload.system:
            conn.system = payload.system

    db.commit()
    db.refresh(conn)
    return ConnectionSchema(
        patientId=conn.patient_id,
        patientName=conn.patient_name,
        patientAbha=conn.patient_abha,
        doctorId=conn.doctor_id,
        doctorName=conn.doctor_name,
        system=conn.system,
    )
