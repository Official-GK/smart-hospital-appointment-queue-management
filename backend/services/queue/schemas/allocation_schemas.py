from typing import Optional, List
from pydantic import BaseModel, Field
from backend.services.queue.models.doctor_workload_models import DoctorAvailability


class DoctorAllocationSuggestion(BaseModel):
    """Ranked suggestion representing an eligible doctor for patient assignment."""
    doctor_id: str
    doctor_name: str
    department_id: str
    availability: str
    active_queue_length: int = Field(..., description="Count of waiting/called patients currently queued for this doctor")
    estimated_wait_minutes: int = Field(..., description="Estimated wait time for next assigned patient")
    completed_today_count: int = Field(default=0, description="Total consultations completed today")
    is_recommended: bool = Field(default=False, description="True for the top-ranked recommendation")
    suitability_reason: str = Field(..., description="Clinical/workload explanation for this ranking")


class DoctorAllocationSuggestResponse(BaseModel):
    """Response containing ranked doctor allocation recommendations for a department specialty."""
    department_id: str
    total_eligible_doctors: int
    suggestions: List[DoctorAllocationSuggestion]


class DoctorAssignmentRequest(BaseModel):
    """Payload for staff to assign or manually reassign/override a patient's doctor."""
    doctor_id: str = Field(..., description="ID of the doctor to assign the patient to", example="DOC-001")
    recorded_by_user_id: str = Field(..., description="ID of staff member making the assignment", example="STF-101")
    notes: Optional[str] = Field(default=None, description="Optional assignment notes or override reason", example="Reassigned due to workload balancing")


class DoctorAvailabilityUpdateRequest(BaseModel):
    """Payload to update a doctor's availability status (AVAILABLE, BUSY, OFF_DUTY, ABSENT)."""
    availability: DoctorAvailability
    doctor_name: Optional[str] = None
    department_id: Optional[str] = None
