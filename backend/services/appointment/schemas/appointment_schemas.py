from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AppointmentStatus(str, Enum):
    SCHEDULED = "Scheduled"
    CHECKED_IN = "Checked-In"
    IN_CONSULTATION = "In-Consultation"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    NO_SHOW = "No-Show"


class SlotStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    RELEASED = "RELEASED"


class OperationalTimestamps(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    check_in_time: Optional[datetime] = None
    queue_entry_time: Optional[datetime] = None
    consultation_start_time: Optional[datetime] = None
    consultation_end_time: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class StatusAuditRecord(BaseModel):
    history_id: str
    appointment_id: str
    from_status: Optional[AppointmentStatus] = None
    to_status: AppointmentStatus
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    changed_by: str = "Staff Member"
    notes: Optional[str] = None
    old_slot_details: Optional[Dict[str, str]] = None
    new_slot_details: Optional[Dict[str, str]] = None


class CancellationDetails(BaseModel):
    reason: str
    cancelled_at: datetime = Field(default_factory=datetime.utcnow)
    cancelled_by: str  # Staff ID
    notes: Optional[str] = None


class AppointmentCancelRequest(BaseModel):
    reason: str
    staff_id: str
    notes: Optional[str] = None


class AppointmentRescheduleRequest(BaseModel):
    staff_id: str
    doctor_id: Optional[str] = None
    appointment_date: Optional[date] = None
    appointment_time: Optional[str] = None
    reason: Optional[str] = "Patient Request"
    notes: Optional[str] = None


class AppointmentCreate(BaseModel):
    patient_id: Optional[str] = None
    patient_name: str
    doctor_id: str
    department_id: str
    appointment_date: date
    appointment_time: str
    priority: str = "Normal"
    notes: Optional[str] = None
    staff_id: Optional[str] = "Staff Member"


class StatusTransitionRequest(BaseModel):
    new_status: AppointmentStatus
    changed_by: str = "Staff Member"
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    appointment_id: str
    patient_id: str
    patient_name: str
    doctor_id: str
    doctor_name: str
    department_id: str
    department_name: str
    appointment_date: date
    appointment_time: str
    status: AppointmentStatus
    priority: str = "Normal"
    token_number: Optional[str] = None
    timestamps: OperationalTimestamps
    notes: Optional[str] = None
    history: List[StatusAuditRecord] = Field(default_factory=list)
    cancellation_details: Optional[CancellationDetails] = None


class SlotInventoryItem(BaseModel):
    doctor_id: str
    appointment_date: date
    slot_time: str
    status: SlotStatus
    appointment_id: Optional[str] = None
    patient_name: Optional[str] = None


class AppointmentStatistics(BaseModel):
    total_appointments: int
    scheduled_count: int
    checked_in_count: int
    in_consultation_count: int
    completed_count: int
    cancelled_count: int
    no_show_count: int
    completion_rate: float
    cancellation_rate: float
    no_show_rate: float
    released_slots_count: int
    reasons_breakdown: Dict[str, int]


class FilterMetadata(BaseModel):
    statuses: List[str]
    departments: List[dict]
    doctors: List[dict]
    cancellation_reasons: List[str] = [
        "Patient Request",
        "Doctor Unavailable",
        "Scheduling Conflict",
        "Medical Emergency",
        "Weather / Transportation Delay",
        "Duplicate Booking",
        "Other",
    ]
