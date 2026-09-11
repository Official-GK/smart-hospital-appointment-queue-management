from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from collections import defaultdict
import uuid
import threading


class JourneyStage(str, Enum):
    """The 8 operational patient journey stages specified for HAQM-82."""
    REGISTRATION = "registration"
    BOOKING = "booking"
    CHECK_IN = "check_in"
    TOKEN_ISSUED = "token_issued"
    CALLED = "called"
    CONSULTATION_START = "consultation_start"
    CONSULTATION_END = "consultation_end"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    NO_SHOW = "no_show"
    PRIORITY_ELEVATED = "priority_elevated"


# frozen=True enforces immutability at the Python runtime level.
# Modifying any attribute after creation will raise a FrozenInstanceError.
@dataclass(frozen=True)
class OperationalTimestampRecord:
    record_id: str
    token_id: str
    patient_id: str
    stage: JourneyStage
    timestamp: datetime
    appointment_id: Optional[str] = None
    doctor_id: Optional[str] = None
    department_id: Optional[str] = None
    recorded_by_user_id: Optional[str] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        token_id: str,
        patient_id: str,
        stage: JourneyStage,
        timestamp: Optional[datetime] = None,
        appointment_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        department_id: Optional[str] = None,
        recorded_by_user_id: Optional[str] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "OperationalTimestampRecord":
        record_time = timestamp or datetime.now(timezone.utc)
        if record_time.tzinfo is None:
            record_time = record_time.replace(tzinfo=timezone.utc)

        return cls(
            record_id=str(uuid.uuid4()),
            token_id=token_id,
            patient_id=patient_id,
            stage=stage,
            timestamp=record_time,
            appointment_id=appointment_id,
            doctor_id=doctor_id,
            department_id=department_id,
            recorded_by_user_id=recorded_by_user_id,
            notes=notes,
            metadata=metadata or {},
        )


class TimestampStore:
    """
    Append-only in-memory storage for operational timestamps.

    DSA Rationale:
    - We use Hash Maps (dict with defaultdict(list)) keyed by token_id and patient_id.
    - Querying a token or patient timeline is O(1) instead of an O(N) linear search over all hospital events.
    - Appending to a list is amortized O(1) and naturally preserves chronological sequence.
    """
    def __init__(self):
        self._by_token: Dict[str, List[OperationalTimestampRecord]] = defaultdict(list)
        self._by_patient: Dict[str, List[OperationalTimestampRecord]] = defaultdict(list)
        self._all_records: List[OperationalTimestampRecord] = []
        self._lock = threading.Lock()

    def append(self, record: OperationalTimestampRecord) -> OperationalTimestampRecord:
        with self._lock:
            self._by_token[record.token_id].append(record)
            self._by_patient[record.patient_id].append(record)
            self._all_records.append(record)
            return record

    def get_by_token(self, token_id: str) -> List[OperationalTimestampRecord]:
        with self._lock:
            return list(self._by_token.get(token_id, []))

    def get_by_patient(self, patient_id: str) -> List[OperationalTimestampRecord]:
        with self._lock:
            return list(self._by_patient.get(patient_id, []))

    def get_all(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[OperationalTimestampRecord]:
        with self._lock:
            results = self._all_records
            if start_time:
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                results = [r for r in results if r.timestamp >= start_time]
            if end_time:
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)
                results = [r for r in results if r.timestamp <= end_time]
            return results

    def clear(self):
        """Reset helper for unit tests."""
        with self._lock:
            self._by_token.clear()
            self._by_patient.clear()
            self._all_records.clear()


timestamp_store = TimestampStore()
