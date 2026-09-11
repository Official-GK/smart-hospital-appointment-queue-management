from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


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
    age: Optional[int] = None
    gender: Optional[str] = "Other"
    phone: str
    address: Optional[str] = None


class PatientCreate(BaseModel):
    """
    Payload for front-desk patient registration
    """
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: Optional[str] = None
    age: Optional[int] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = "Other"
    phone: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None
    identifier: Optional[str] = None

    @model_validator(mode="after")
    def validate_and_normalize(self):
        # Resolve names
        if not self.first_name and not self.name:
            raise ValueError("Patient first name or full name is required")
        if not self.first_name and self.name:
            parts = self.name.strip().split(" ", 1)
            self.first_name = parts[0]
            if not self.last_name:
                self.last_name = parts[1] if len(parts) > 1 else ""
        if not self.last_name:
            self.last_name = ""

        # Resolve contact number
        resolved_phone = self.phone or self.contact_number
        if not resolved_phone or not resolved_phone.strip():
            raise ValueError("Contact number (phone) is required")
        self.phone = resolved_phone.strip()

        # Compute age or date_of_birth if only one is provided
        if self.age is not None and self.date_of_birth is None:
            today = date.today()
            self.date_of_birth = date(today.year - self.age, 1, 1)
        elif self.date_of_birth is not None and self.age is None:
            today = date.today()
            dob = self.date_of_birth
            self.age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        return self


class DuplicateCheckResponse(BaseModel):
    """
    Response model for pre-flight duplicate registration checks
    """
    is_duplicate: bool
    existing_patient_id: Optional[str] = None
    existing_patient_name: Optional[str] = None
    matched_field: Optional[str] = None
    message: str


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


class PatientAuditRecord(BaseModel):
    """
    Field-level audit log entry for changes to patient records
    """
    audit_id: str
    patient_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    changed_by: str
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    notes: Optional[str] = None


class PatientUpdateRequest(BaseModel):
    """
    Request payload to update demographic and contact details
    """
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    updated_by: Optional[str] = "Authorized Staff"
    notes: Optional[str] = None


class TokenHistoryItem(BaseModel):
    """
    Token record associated with a patient visit
    """
    token_id: str
    token_number: str
    appointment_id: Optional[str] = None
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    priority: str = "Normal"
    status: str = "Waiting"
    created_at: Optional[datetime] = None


class VisitHistoryItem(BaseModel):
    """
    Medical visit entry with full operational timestamps
    """
    appointment_id: str
    appointment_date: date
    appointment_time: str
    doctor_id: str
    doctor_name: str
    department_id: str
    department_name: str
    status: str
    priority: str
    is_walk_in: bool
    booking_time: Optional[datetime] = None
    check_in_time: Optional[datetime] = None
    queue_entry_time: Optional[datetime] = None
    consultation_start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    notes: Optional[str] = None


class PatientProfileResponse(BaseModel):
    """
    Comprehensive patient profile view for authorized staff
    """
    patient_id: str
    first_name: str
    last_name: str
    patient_name: str
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    phone: str
    address: Optional[str] = None
    status: PatientStatus = PatientStatus.REGISTERED
    created_at: datetime
    last_arrival_time: Optional[datetime] = None
    is_masked: bool = False
    active_appointments: List[VisitHistoryItem] = Field(default_factory=list)
    visit_history: List[VisitHistoryItem] = Field(default_factory=list)
    token_history: List[TokenHistoryItem] = Field(default_factory=list)
    audit_trail: List[PatientAuditRecord] = Field(default_factory=list)

