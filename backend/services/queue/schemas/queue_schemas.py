from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class QueueStatus(str, Enum):
    WAITING = "Waiting"
    CALLED = "Called"
    IN_CONSULTATION = "In Consultation"
    COMPLETED = "Completed"
    NO_SHOW = "No-Show"
    ABANDONED = "Abandoned"


class QueuePriority(str, Enum):
    NORMAL = "Normal"
    SENIOR = "Senior"
    EMERGENCY = "Emergency"


class QueueToken(BaseModel):
    token_id: str
    token_number: str
    appointment_id: str
    patient_id: str
    patient_name: str
    doctor_id: str
    doctor_name: str
    department_id: str
    department_name: str
    priority: QueuePriority = QueuePriority.NORMAL
    status: QueueStatus = QueueStatus.WAITING
    queue_entry_time: datetime = Field(default_factory=datetime.utcnow)
    called_time: Optional[datetime] = None
    consultation_start_time: Optional[datetime] = None
    consultation_end_time: Optional[datetime] = None
    estimated_wait_minutes: int = 15
