from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from backend.services.queue.schemas.queue_schemas import QueueToken


class NoShowRequest(BaseModel):
    """Payload to flag a patient who failed to appear when called as No-Show."""
    recorded_by_user_id: Optional[str] = Field(default=None, description="ID of staff member or doctor logging the no-show")
    staff_id: Optional[str] = Field(default=None, description="Staff identifier alias")
    reason: Optional[str] = Field(default=None, description="Optional note or explanation")

    def get_recorded_by_user_id(self) -> str:
        uid = self.recorded_by_user_id or self.staff_id
        if not uid:
            raise ValueError("recorded_by_user_id or staff_id must be provided")
        return uid


class NoShowRecordResponse(BaseModel):
    """Response returned when a token is successfully marked as No-Show."""
    token: QueueToken
    no_show_time: datetime
    recorded_by_user_id: str
    reason: Optional[str] = None


class NoShowAnalyticsResponse(BaseModel):
    """Aggregated no-show reporting metrics for hospital operations."""
    total_tokens_tracked: int
    total_no_shows: int
    no_show_rate_pct: float
    by_department: Dict[str, int] = Field(default_factory=dict)
    by_doctor: Dict[str, int] = Field(default_factory=dict)
    reasons_breakdown: Dict[str, int] = Field(default_factory=dict)


class PatientNoShowHistoryResponse(BaseModel):
    """Patient-level no-show history log for patient profile and reliability tracking."""
    patient_id: str
    total_no_shows: int
    records: List[Dict[str, Any]] = Field(default_factory=list)
