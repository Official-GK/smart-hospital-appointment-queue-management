from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from backend.services.queue.models.timestamp_models import JourneyStage


class TimestampRecordCreate(BaseModel):
    """Schema for recording an operational timestamp at a journey stage."""
    token_id: str = Field(..., description="Token identifier")
    patient_id: str = Field(..., description="Patient identifier")
    stage: JourneyStage = Field(..., description="Journey stage")
    timestamp: Optional[datetime] = Field(default=None, description="Event time (UTC). Defaults to now.")
    appointment_id: Optional[str] = None
    doctor_id: Optional[str] = None
    department_id: Optional[str] = None
    recorded_by_user_id: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TimestampRecordResponse(BaseModel):
    """Schema representing an immutable operational timestamp record."""
    record_id: str
    token_id: str
    patient_id: str
    stage: str
    timestamp: datetime
    appointment_id: Optional[str] = None
    doctor_id: Optional[str] = None
    department_id: Optional[str] = None
    recorded_by_user_id: Optional[str] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class StageDurationMetrics(BaseModel):
    """Computed waiting time and consultation duration metrics."""
    waiting_time_seconds: Optional[float] = None
    waiting_time_minutes: Optional[float] = None
    consultation_duration_seconds: Optional[float] = None
    consultation_duration_minutes: Optional[float] = None
    total_journey_duration_seconds: Optional[float] = None
    total_journey_duration_minutes: Optional[float] = None
    stage_intervals_seconds: Dict[str, float] = Field(default_factory=dict)


class TokenTimelineResponse(BaseModel):
    """Complete audit timeline and computed duration metrics for a queue token."""
    token_id: str
    patient_id: str
    current_stage: Optional[str] = None
    is_completed: bool = False
    metrics: StageDurationMetrics
    timeline: List[TimestampRecordResponse]


class OperationalAnalyticsResponse(BaseModel):
    """Aggregated operational metrics for reports and management dashboards."""
    total_tokens_tracked: int
    completed_consultations: int
    avg_waiting_time_minutes: float
    avg_consultation_time_minutes: float
    doctor_throughput: Dict[str, int] = Field(default_factory=dict)
    stage_counts: Dict[str, int] = Field(default_factory=dict)
