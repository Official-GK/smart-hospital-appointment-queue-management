from datetime import datetime, timezone
from typing import Optional, List, Tuple
from fastapi import HTTPException

from backend.services.queue.models.visit_history_models import visit_history_store
from backend.services.queue.schemas.queue_schemas import QueueStatus, QueuePriority, QueueToken
from backend.services.queue.schemas.waiting_time_schemas import WaitTimeResponse
from backend.services.queue.services.queue_service import queue_service_instance, _normalize_datetime


DEFAULT_BENCHMARK_CONSULTATION_MINUTES = 10.0


class WaitingTimeService:
    """
    Service responsible for calculating dynamic, data-driven estimated waiting times.
    Formula: Estimated Wait Time = (Patients Ahead) × (Average Consultation Duration).
    """

    def get_average_consultation_duration(
        self,
        doctor_id: Optional[str],
        department_id: Optional[str],
    ) -> Tuple[float, str]:
        """
        Acceptance Criteria 1:
        Fallback Chain:
        1. Doctor-specific rolling average of last N (up to 10) completed visits.
        2. Department-level average across completed visits.
        3. Default clinical benchmark (10.0 minutes).
        """
        # Tier 1: Doctor-specific rolling average
        if doctor_id:
            doctor_visits = visit_history_store.get_by_doctor(doctor_id)
            if doctor_visits:
                recent = doctor_visits[-10:]
                durations = [v.duration_minutes for v in recent if v.duration_minutes > 0]
                if durations:
                    avg = round(sum(durations) / len(durations), 1)
                    return avg, "doctor_average"

        # Tier 2: Department-level average
        if department_id:
            all_visits = visit_history_store.get_all()
            dept_visits = [v for v in all_visits if v.department_id == department_id]
            if dept_visits:
                recent_dept = dept_visits[-20:]
                dept_durations = [v.duration_minutes for v in recent_dept if v.duration_minutes > 0]
                if dept_durations:
                    avg = round(sum(dept_durations) / len(dept_durations), 1)
                    return avg, "department_average"

        # Tier 3: Default clinical benchmark
        return DEFAULT_BENCHMARK_CONSULTATION_MINUTES, "default_benchmark"

    def get_ordered_active_queue(
        self,
        doctor_id: Optional[str] = None,
        department_id: Optional[str] = None,
    ) -> List[QueueToken]:
        """
        Centralized helper sorting the active waiting queue by:
        1. Priority: EMERGENCY (0), SENIOR (1), NORMAL (2)
        2. Entry time: Earliest queue_entry_time first.
        """
        active_statuses = {QueueStatus.WAITING, QueueStatus.CALLED}
        with queue_service_instance._lock:
            tokens = [
                t for t in queue_service_instance._tokens.values()
                if t.status in active_statuses
            ]

        if doctor_id:
            tokens = [t for t in tokens if t.doctor_id == doctor_id]
        elif department_id:
            tokens = [t for t in tokens if t.department_id == department_id]

        def priority_weight(p: QueuePriority) -> int:
            # HAQM-73 5-tier queue prioritization:
            # Emergency (0) > Senior Citizen (1) > VIP (2) > Scheduled (3) > Walk-in (4)
            if p == QueuePriority.EMERGENCY:
                return 0
            if p in {QueuePriority.SENIOR_CITIZEN, QueuePriority.SENIOR}:
                return 1
            if p == QueuePriority.VIP:
                return 2
            if p in {QueuePriority.SCHEDULED, QueuePriority.NORMAL}:
                return 3
            if p == QueuePriority.WALK_IN:
                return 4
            return 3


        tokens.sort(
            key=lambda t: (
                priority_weight(t.priority),
                _normalize_datetime(t.queue_entry_time) or datetime.now(timezone.utc),
            )
        )
        return tokens

    def calculate_token_wait_time(self, token_identifier: str) -> WaitTimeResponse:
        """
        Calculates wait time for a specific patient token:
        Wait Time = (Patients Ahead) × (Average Consultation Duration).
        """
        token = self._find_token(token_identifier)
        if not token:
            raise HTTPException(status_code=404, detail=f"Token '{token_identifier}' not found in queue")

        # Inactive or in-consultation tokens have 0 wait time
        if token.status in {QueueStatus.COMPLETED, QueueStatus.NO_SHOW, QueueStatus.ABANDONED, QueueStatus.IN_CONSULTATION}:
            avg_duration, source = self.get_average_consultation_duration(token.doctor_id, token.department_id)
            return WaitTimeResponse(
                token_id=token.token_id,
                token_number=token.token_number,
                patients_ahead=0,
                average_consultation_minutes=avg_duration,
                estimated_wait_minutes=0,
                calculation_source=source,
                doctor_id=token.doctor_id,
                department_id=token.department_id,
            )

        # Get ordered queue for this doctor / department
        ordered = self.get_ordered_active_queue(doctor_id=token.doctor_id)
        token_index = next((i for i, t in enumerate(ordered) if t.token_id == token.token_id), None)

        if token_index is None:
            patients_ahead = 0
        else:
            patients_ahead = token_index

        # Check if another patient is currently in consultation with this doctor
        with queue_service_instance._lock:
            in_consult = any(
                t.doctor_id == token.doctor_id and t.status == QueueStatus.IN_CONSULTATION
                for t in queue_service_instance._tokens.values()
            )

        effective_ahead = patients_ahead + (1 if in_consult else 0)

        avg_duration, source = self.get_average_consultation_duration(token.doctor_id, token.department_id)
        estimated_minutes = int(round(effective_ahead * avg_duration))

        # Update the token's estimated_wait_minutes field in place
        token.estimated_wait_minutes = estimated_minutes

        return WaitTimeResponse(
            token_id=token.token_id,
            token_number=token.token_number,
            patients_ahead=effective_ahead,
            average_consultation_minutes=avg_duration,
            estimated_wait_minutes=estimated_minutes,
            calculation_source=source,
            doctor_id=token.doctor_id,
            department_id=token.department_id,
        )

    def recalculate_queue_wait_times(
        self,
        doctor_id: Optional[str] = None,
        department_id: Optional[str] = None,
    ):
        """
        Acceptance Criteria 2 & 4:
        Recalculates wait times dynamically for all active tokens assigned to a doctor or department.
        Replaces the old placeholder in abandonment_service.py and queue_service.py.
        """
        ordered = self.get_ordered_active_queue(doctor_id=doctor_id, department_id=department_id)
        if not ordered:
            return

        with queue_service_instance._lock:
            in_consult = any(
                (t.doctor_id == doctor_id or t.department_id == department_id) and t.status == QueueStatus.IN_CONSULTATION
                for t in queue_service_instance._tokens.values()
            )

        doc_id = doctor_id or (ordered[0].doctor_id if ordered else None)
        dept_id = department_id or (ordered[0].department_id if ordered else None)
        avg_duration, _ = self.get_average_consultation_duration(doc_id, dept_id)

        for idx, token in enumerate(ordered):
            effective_ahead = idx + (1 if in_consult else 0)
            token.estimated_wait_minutes = int(round(effective_ahead * avg_duration))

    def _find_token(self, token_identifier: str) -> Optional[QueueToken]:
        with queue_service_instance._lock:
            for t in queue_service_instance._tokens.values():
                if t.token_id == token_identifier or t.appointment_id == token_identifier:
                    return t
        return queue_service_instance.get_token_by_appointment(token_identifier)


waiting_time_service_instance = WaitingTimeService()
