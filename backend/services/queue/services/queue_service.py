import threading
from datetime import datetime
from typing import Dict, List, Optional
from backend.services.queue.schemas.queue_schemas import QueuePriority, QueueStatus, QueueToken


class QueueService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(QueueService, cls).__new__(cls)
                cls._instance._tokens: Dict[str, QueueToken] = {}
                cls._instance._token_counter = 100
                cls._instance._init_seed_tokens()
        return cls._instance

    def _init_seed_tokens(self):
        # Initial seed tokens for live dashboard visibility
        seed_tokens = [
            QueueToken(
                token_id="TOK-101",
                token_number="A-101",
                appointment_id="APT-002",
                patient_id="PAT-002",
                patient_name="Michael Chen",
                doctor_id="DOC-001",
                doctor_name="Dr. Sarah Smith",
                department_id="DEP-CARD",
                department_name="Cardiology",
                priority=QueuePriority.NORMAL,
                status=QueueStatus.WAITING,
                queue_entry_time=datetime.utcnow(),
                estimated_wait_minutes=10,
            ),
            QueueToken(
                token_id="TOK-102",
                token_number="A-102",
                appointment_id="APT-003",
                patient_id="PAT-003",
                patient_name="Elena Rodriguez",
                doctor_id="DOC-002",
                doctor_name="Dr. Marcus Johnson",
                department_id="DEP-ORTHO",
                department_name="Orthopedics",
                priority=QueuePriority.EMERGENCY,
                status=QueueStatus.IN_CONSULTATION,
                queue_entry_time=datetime.utcnow(),
                consultation_start_time=datetime.utcnow(),
                estimated_wait_minutes=0,
            ),
        ]
        for t in seed_tokens:
            self._tokens[t.appointment_id] = t

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
                queue_entry_time=datetime.utcnow(),
                estimated_wait_minutes=max(5, (len([t for t in self._tokens.values() if t.status == QueueStatus.WAITING]) + 1) * 10),
            )
            self._tokens[appointment_id] = token
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
            return token

    def get_token_by_appointment(self, appointment_id: str) -> Optional[QueueToken]:
        return self._tokens.get(appointment_id)

    def get_live_queue(self, department_id: Optional[str] = None, doctor_id: Optional[str] = None) -> List[QueueToken]:
        active_statuses = {QueueStatus.WAITING, QueueStatus.CALLED, QueueStatus.IN_CONSULTATION}
        tokens = [t for t in self._tokens.values() if t.status in active_statuses]
        if department_id:
            tokens = [t for t in tokens if t.department_id == department_id]
        if doctor_id:
            tokens = [t for t in tokens if t.doctor_id == doctor_id]
        # Sort Emergency first, then entry time
        tokens.sort(key=lambda t: (0 if t.priority == QueuePriority.EMERGENCY else 1, t.queue_entry_time))
        return tokens


queue_service_instance = QueueService()
