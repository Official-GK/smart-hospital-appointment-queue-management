from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, List
import threading


class DoctorAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFF_DUTY = "OFF_DUTY"
    ABSENT = "ABSENT"


@dataclass
class DoctorWorkloadRecord:
    doctor_id: str
    doctor_name: str
    department_id: Optional[str] = None
    availability: DoctorAvailability = DoctorAvailability.AVAILABLE
    completed_consultations_count: int = 0
    total_consultation_seconds: float = 0.0
    last_completed_at: Optional[datetime] = None
    active_token_id: Optional[str] = None


class DoctorWorkloadStore:
    """
    Lightweight, thread-safe in-memory store tracking doctor availability and completed workload.
    Supports HAQM-79 (completion lifecycle) and HAQM-74 (doctor allocation and absence exclusion).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._doctors: Dict[str, DoctorWorkloadRecord] = {}

    def register_doctor(
        self,
        doctor_id: str,
        doctor_name: str,
        department_id: str,
        availability: DoctorAvailability = DoctorAvailability.AVAILABLE,
    ) -> DoctorWorkloadRecord:
        with self._lock:
            if doctor_id not in self._doctors:
                self._doctors[doctor_id] = DoctorWorkloadRecord(
                    doctor_id=doctor_id,
                    doctor_name=doctor_name,
                    department_id=department_id,
                    availability=availability,
                )
            else:
                doc = self._doctors[doctor_id]
                doc.doctor_name = doctor_name
                doc.department_id = department_id
                doc.availability = availability
            return self._doctors[doctor_id]

    def set_availability(
        self,
        doctor_id: str,
        availability: DoctorAvailability,
        doctor_name: Optional[str] = None,
        department_id: Optional[str] = None,
    ) -> DoctorWorkloadRecord:
        with self._lock:
            if doctor_id not in self._doctors:
                self._doctors[doctor_id] = DoctorWorkloadRecord(
                    doctor_id=doctor_id,
                    doctor_name=doctor_name or f"Doctor {doctor_id}",
                    department_id=department_id,
                    availability=availability,
                )
            doc = self._doctors[doctor_id]
            doc.availability = availability
            if doctor_name:
                doc.doctor_name = doctor_name
            if department_id:
                doc.department_id = department_id
            return doc

    def set_busy(self, doctor_id: str, doctor_name: str, token_id: str, department_id: Optional[str] = None):
        with self._lock:
            if doctor_id not in self._doctors:
                self._doctors[doctor_id] = DoctorWorkloadRecord(
                    doctor_id=doctor_id,
                    doctor_name=doctor_name,
                    department_id=department_id,
                )
            doc = self._doctors[doctor_id]
            doc.doctor_name = doctor_name
            doc.availability = DoctorAvailability.BUSY
            doc.active_token_id = token_id
            if department_id:
                doc.department_id = department_id

    def mark_completed_and_available(
        self,
        doctor_id: str,
        doctor_name: str,
        duration_seconds: float,
        department_id: Optional[str] = None,
    ) -> DoctorWorkloadRecord:
        with self._lock:
            if doctor_id not in self._doctors:
                self._doctors[doctor_id] = DoctorWorkloadRecord(
                    doctor_id=doctor_id,
                    doctor_name=doctor_name,
                    department_id=department_id,
                )
            doc = self._doctors[doctor_id]
            doc.doctor_name = doctor_name
            doc.availability = DoctorAvailability.AVAILABLE
            doc.completed_consultations_count += 1
            doc.total_consultation_seconds += max(0.0, duration_seconds)
            doc.last_completed_at = datetime.now(timezone.utc)
            doc.active_token_id = None
            if department_id:
                doc.department_id = department_id
            return doc

    def get_doctor_workload(self, doctor_id: str) -> Optional[DoctorWorkloadRecord]:
        with self._lock:
            return self._doctors.get(doctor_id)

    def get_doctors_by_department(self, department_id: str) -> List[DoctorWorkloadRecord]:
        with self._lock:
            return [d for d in self._doctors.values() if d.department_id == department_id]

    def get_all(self) -> List[DoctorWorkloadRecord]:
        with self._lock:
            return list(self._doctors.values())

    def clear(self):
        with self._lock:
            self._doctors.clear()


doctor_workload_store = DoctorWorkloadStore()
