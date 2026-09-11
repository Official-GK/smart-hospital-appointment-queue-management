from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"


class PatientStatus(str, Enum):
    REGISTERED = "Registered"
    CHECKED_IN = "Checked-In"
    IN_CONSULTATION = "In-Consultation"
    COMPLETED = "Completed"
    INACTIVE = "Inactive"


class PatientBase(BaseModel):
    """
    Core demographic data conforming to TECHNICAL_CONTRACTS.md Section 7
    """
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = "Other"
    phone: str
    address: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientResponse(PatientBase):
    patient_id: str
    patient_name: str
    status: PatientStatus = PatientStatus.REGISTERED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_arrival_time: Optional[datetime] = None


class PatientCheckInRequest(BaseModel):
    """
    Payload for front-desk staff check-in action
    """
    patient_id: Optional[str] = None
    appointment_id: Optional[str] = None
    patient_name: Optional[str] = None
    phone: Optional[str] = None
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    priority: str = "Normal"  # "Normal" or "Emergency"
    is_walk_in: bool = False
    arrival_time: Optional[datetime] = None
    notes: Optional[str] = None
    checked_in_by: Optional[str] = "Front-Desk Staff"


class PatientCheckInResponse(BaseModel):
    """
    Confirmation receipt returned when a patient is checked in
    """
    check_in_id: str
    patient_id: str
    patient_name: str
    appointment_id: Optional[str] = None
    status: str = "Checked-In"
    arrival_time: datetime
    token_id: Optional[str] = None
    token_number: Optional[str] = None
    queue_position: Optional[int] = None
    estimated_wait_minutes: Optional[int] = None
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    priority: str = "Normal"
    is_walk_in: bool = False
    notes: Optional[str] = None


class EligibleCheckInItem(BaseModel):
    """
    Model for arriving patients awaiting check-in
    """
    appointment_id: str
    patient_id: str
    patient_name: str
    phone: Optional[str] = None
    appointment_date: date
    appointment_time: str
    doctor_id: str
    doctor_name: str
    department_id: str
    department_name: str
    priority: str = "Normal"
    is_walk_in: bool = False
    status: str
    can_check_in: bool = True
