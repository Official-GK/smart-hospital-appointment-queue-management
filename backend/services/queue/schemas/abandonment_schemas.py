from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field
from backend.services.queue.schemas.queue_schemas import QueueStatus, QueueToken


class AbandonmentRequest(BaseModel):
    """Payload to flag a patient as abandoned."""
    reason: Optional[str] = Field(default=None, description="Optional reason why the patient left")
    recorded_by_user_id: Optional[str] = Field(default=None, description="Staff member logging the abandonment")


class AbandonmentRecordResponse(BaseModel):
    """Response returned when a token is successfully flagged as abandoned."""
    token: QueueToken
    abandonment_time: datetime
    waiting_duration_seconds: float
    waiting_duration_minutes: float
    reason: Optional[str] = None
    recorded_by_user_id: Optional[str] = None


class AbandonmentAnalyticsResponse(BaseModel):
    """Aggregated abandonment reporting data for hospital management."""
    total_tokens_tracked: int
    total_abandoned: int
    abandonment_rate_pct: float
    avg_waiting_duration_minutes: float
    by_department: Dict[str, int] = Field(default_factory=dict)
    by_doctor: Dict[str, int] = Field(default_factory=dict)
    reasons_breakdown: Dict[str, int] = Field(default_factory=dict)
