from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, List
from collections import defaultdict
import uuid
import threading


@dataclass(frozen=True)
class VisitRecord:
    """
    Immutable archived record of a completed patient consultation visit.
    Adheres to the same frozen dataclass pattern as OperationalTimestampRecord.
    """
    visit_id: str
    token_id: str
    appointment_id: str
    patient_id: str
    patient_name: str
    doctor_id: str
    doctor_name: str
    department_id: str
    department_name: str
    consultation_start_time: datetime
    consultation_end_time: datetime
    duration_seconds: float
    duration_minutes: float
    recorded_by_user_id: str
    notes: Optional[str] = None
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        token_id: str,
        appointment_id: str,
        patient_id: str,
        patient_name: str,
        doctor_id: str,
        doctor_name: str,
        department_id: str,
        department_name: str,
        consultation_start_time: datetime,
        consultation_end_time: datetime,
        duration_seconds: float,
        recorded_by_user_id: str,
        notes: Optional[str] = None,
    ) -> "VisitRecord":
        return cls(
            visit_id=f"VISIT-{uuid.uuid4().hex[:8].upper()}",
            token_id=token_id,
            appointment_id=appointment_id,
            patient_id=patient_id,
            patient_name=patient_name,
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            department_id=department_id,
            department_name=department_name,
            consultation_start_time=consultation_start_time,
            consultation_end_time=consultation_end_time,
            duration_seconds=max(0.0, duration_seconds),
            duration_minutes=round(max(0.0, duration_seconds) / 60.0, 2),
            recorded_by_user_id=recorded_by_user_id,
            notes=notes,
        )


class VisitHistoryStore:
    """
    Thread-safe, append-only in-memory archive store for completed patient visits.
    Features O(1) hash map indexing by patient_id, doctor_id, and token_id.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._records: List[VisitRecord] = []
        self._by_patient: Dict[str, List[VisitRecord]] = defaultdict(list)
        self._by_doctor: Dict[str, List[VisitRecord]] = defaultdict(list)
        self._by_token: Dict[str, VisitRecord] = {}

    def append(self, record: VisitRecord):
        with self._lock:
            self._records.append(record)
            self._by_patient[record.patient_id].append(record)
            self._by_doctor[record.doctor_id].append(record)
            self._by_token[record.token_id] = record

    def get_by_patient(self, patient_id: str) -> List[VisitRecord]:
        with self._lock:
            return list(self._by_patient.get(patient_id, []))

    def get_by_doctor(self, doctor_id: str) -> List[VisitRecord]:
        with self._lock:
            return list(self._by_doctor.get(doctor_id, []))

    def get_by_token(self, token_id: str) -> Optional[VisitRecord]:
        with self._lock:
            return self._by_token.get(token_id)

    def get_all(self) -> List[VisitRecord]:
        with self._lock:
            return list(self._records)

    def clear(self):
        with self._lock:
            self._records.clear()
            self._by_patient.clear()
            self._by_doctor.clear()
            self._by_token.clear()


visit_history_store = VisitHistoryStore()
