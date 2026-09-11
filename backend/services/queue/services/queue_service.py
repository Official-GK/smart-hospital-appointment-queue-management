import threading
from datetime import datetime
from typing import Dict, List, Optional
from backend.database.token_fetcher import (
    fetch_live_queue_tokens,
    fetch_token_by_appointment,
    save_token,
)
from backend.services.queue.schemas.queue_schemas import QueuePriority, QueueStatus, QueueToken


def _normalize_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is not None and getattr(dt, "tzinfo", None) is not None:
        return dt.replace(tzinfo=None)
    return dt


class QueueService:
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(QueueService, cls).__new__(cls)
                cls._instance._tokens: Dict[str, QueueToken] = {}
                cls._instance._token_counter = 100
                cls._instance._init_seed_tokens()
        return cls._instance

    def _init_seed_tokens(self):
        # Tokens must not be mock demo data; they are fetched from PostgreSQL or created upon check-in
        self._tokens = {}

    def add_to_queue(
        self,
        appointment_id: str,
        patient_id: str,
        patient_name: str,
        doctor_id: str,
        doctor_name: str,
        department_id: str,
        department_name: str,
        priority: QueuePriority = QueuePriority.NORMAL,
        is_walk_in: bool = False,
    ) -> QueueToken:
        with self._lock:
            self._token_counter += 1
            token_code = f"T-{self._token_counter}"
            token = QueueToken(
                token_id=f"TOK-{self._token_counter}",
                token_number=token_code,
                appointment_id=appointment_id,
                patient_id=patient_id,
                patient_name=patient_name,
                doctor_id=doctor_id,
                doctor_name=doctor_name,
                department_id=department_id,
                department_name=department_name,
                priority=priority,
                status=QueueStatus.WAITING,
                is_walk_in=is_walk_in,
                queue_entry_time=datetime.utcnow(),
                estimated_wait_minutes=10,
            )
            self._tokens[appointment_id] = token

            # Calculate dynamic wait time using WaitingTimeService (HAQM-75)
            try:
                from backend.services.queue.services.waiting_time_service import waiting_time_service_instance
                wait_info = waiting_time_service_instance.calculate_token_wait_time(token.token_id)
                token.estimated_wait_minutes = wait_info.estimated_wait_minutes
            except Exception:
                pass

            # Persist to PostgreSQL database (handled gracefully with try...except)
            try:
                save_token({
                    "token_id": token.token_id,
                    "token_number": token.token_number,
                    "appointment_id": token.appointment_id,
                    "patient_id": token.patient_id,
                    "patient_name": token.patient_name,
                    "doctor_id": token.doctor_id,
                    "doctor_name": token.doctor_name,
                    "department_id": token.department_id,
                    "department_name": token.department_name,
                    "priority": token.priority.value if hasattr(token.priority, "value") else str(token.priority),
                    "status": token.status.value if hasattr(token.status, "value") else str(token.status),
                    "queue_entry_time": token.queue_entry_time.isoformat(),
                    "estimated_wait_minutes": token.estimated_wait_minutes,
                })
            except Exception:
                pass

            return token

    def update_queue_status(
        self,
        appointment_id: str,
        status: QueueStatus,
        consultation_start_time: Optional[datetime] = None,
        consultation_end_time: Optional[datetime] = None,
    ) -> Optional[QueueToken]:
        with self._lock:
            token = self._tokens.get(appointment_id)
            if not token:
                return None
            token.status = status
            if consultation_start_time:
                token.consultation_start_time = consultation_start_time
            if consultation_end_time:
                token.consultation_end_time = consultation_end_time

            # Recalculate remaining wait times dynamically (HAQM-75)
            try:
                from backend.services.queue.services.waiting_time_service import waiting_time_service_instance
                waiting_time_service_instance.recalculate_queue_wait_times(
                    doctor_id=token.doctor_id,
                    department_id=token.department_id,
                )
            except Exception:
                pass

            # Persist status update to PostgreSQL
            try:
                save_token({
                    "token_id": token.token_id,
                    "token_number": token.token_number,
                    "appointment_id": token.appointment_id,
                    "patient_id": token.patient_id,
                    "status": token.status.value if hasattr(token.status, "value") else str(token.status),
                    "consultation_start_time": consultation_start_time,
                    "consultation_end_time": consultation_end_time,
                })
            except Exception:
                pass

            return token

    def get_token(self, token_identifier: str) -> Optional[QueueToken]:
        with self._lock:
            for t in self._tokens.values():
                if t.token_id == token_identifier or t.appointment_id == token_identifier:
                    return t
        return self.get_token_by_appointment(token_identifier)

    def get_token_by_appointment(self, appointment_id: str) -> Optional[QueueToken]:
        # Attempt PostgreSQL fetch first with graceful fallback
        try:
            db_data = fetch_token_by_appointment(appointment_id)
            if db_data:
                return QueueToken(
                    token_id=db_data["token_id"],
                    token_number=db_data["token_number"],
                    appointment_id=db_data.get("appointment_id") or appointment_id,
                    patient_id=db_data["patient_id"],
                    patient_name=db_data.get("patient_name") or "",
                    doctor_id=db_data["doctor_id"],
                    doctor_name=db_data.get("doctor_name") or "",
                    department_id=db_data["department_id"],
                    department_name=db_data.get("department_name") or "",
                    priority=QueuePriority(db_data.get("priority", "Normal")),
                    status=QueueStatus(db_data.get("status", "Waiting")),
                    queue_entry_time=_normalize_datetime(db_data.get("queue_entry_time")) or datetime.utcnow(),
                    called_time=_normalize_datetime(db_data.get("called_time")),
                    consultation_start_time=_normalize_datetime(db_data.get("consultation_start_time")),
                    consultation_end_time=_normalize_datetime(db_data.get("consultation_end_time")),
                    estimated_wait_minutes=db_data.get("estimated_wait_minutes") or 15,
                )
        except Exception:
            pass
        return self._tokens.get(appointment_id)

    def get_live_queue(self, department_id: Optional[str] = None, doctor_id: Optional[str] = None) -> List[QueueToken]:
        # Merge in-memory tokens and PostgreSQL tokens
        combined: Dict[str, QueueToken] = dict(self._tokens)

        try:
            db_tokens = fetch_live_queue_tokens(department_id=department_id, doctor_id=doctor_id)
            for t in db_tokens:
                apt_id = t.get("appointment_id")
                if apt_id and apt_id not in combined:
                    combined[apt_id] = QueueToken(
                        token_id=t["token_id"],
                        token_number=t["token_number"],
                        appointment_id=apt_id,
                        patient_id=t["patient_id"],
                        patient_name=t.get("patient_name") or "",
                        doctor_id=t["doctor_id"],
                        doctor_name=t.get("doctor_name") or "",
                        department_id=t["department_id"],
                        department_name=t.get("department_name") or "",
                        priority=QueuePriority(t.get("priority", "Normal")),
                        status=QueueStatus(t.get("status", "Waiting")),
                        queue_entry_time=_normalize_datetime(t.get("queue_entry_time")) or datetime.utcnow(),
                        called_time=_normalize_datetime(t.get("called_time")),
                        consultation_start_time=_normalize_datetime(t.get("consultation_start_time")),
                        consultation_end_time=_normalize_datetime(t.get("consultation_end_time")),
                        estimated_wait_minutes=t.get("estimated_wait_minutes") or 15,
                    )
        except Exception:
            pass

        active_statuses = {QueueStatus.WAITING, QueueStatus.CALLED, QueueStatus.IN_CONSULTATION}
        tokens = [t for t in combined.values() if t.status in active_statuses]
        if department_id:
            tokens = [t for t in tokens if t.department_id == department_id]
        if doctor_id:
            tokens = [t for t in tokens if t.doctor_id == doctor_id]
        # Sort Emergency first, then entry time
        tokens.sort(key=lambda t: (0 if t.priority == QueuePriority.EMERGENCY else 1, _normalize_datetime(t.queue_entry_time) or datetime.utcnow()))
        return tokens


queue_service_instance = QueueService()
