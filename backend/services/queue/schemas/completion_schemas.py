from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from backend.services.queue.schemas.queue_schemas import QueueToken


class CompletionRequest(BaseModel):
    """Payload to conclude consultation and transition patient to Completed status."""
    recorded_by_user_id: str = Field(..., description="ID of doctor or staff ending the consultation", example="DOC-101")
    notes: Optional[str] = Field(default=None, description="Optional clinical/consultation summary notes", example="Prescription issued, review in 2 weeks")


class CompletionRecordResponse(BaseModel):
    """Response returned when a consultation is successfully completed."""
    token: QueueToken
    consultation_duration_seconds: float
    consultation_duration_minutes: float
    archived_visit_id: str
    doctor_availability: str
    recorded_by_user_id: str
    notes: Optional[str] = None


class CompletedAnalyticsResponse(BaseModel):
    """Aggregated completion metrics for operational reporting."""
    total_completed: int
    average_duration_seconds: float
    average_duration_minutes: float
    by_department: Dict[str, int] = Field(default_factory=dict)
    by_doctor: Dict[str, int] = Field(default_factory=dict)


class PatientVisitHistoryResponse(BaseModel):
    """Patient-level archival visit history for medical record tracking."""
    patient_id: str
    total_visits: int
    visits: List[Dict[str, Any]] = Field(default_factory=list)


class DoctorWorkloadResponse(BaseModel):
    """Workload and availability snapshot for a specific doctor."""
    doctor_id: str
    doctor_name: str
    availability: str
    completed_consultations_count: int
    total_consultation_seconds: float
    last_completed_at: Optional[datetime] = None
