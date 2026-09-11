from datetime import datetime, timezone
from typing import Optional, Dict, List
from fastapi import HTTPException

from backend.services.queue.models.timestamp_models import (
    JourneyStage,
    OperationalTimestampRecord,
    timestamp_store,
)
from backend.services.queue.schemas.queue_schemas import QueuePriority, QueueStatus, QueueToken
from backend.services.queue.schemas.abandonment_schemas import (
    AbandonmentRecordResponse,
    AbandonmentAnalyticsResponse,
)
from backend.services.queue.services.queue_service import queue_service_instance, _normalize_datetime
from backend.database.token_fetcher import save_token


class AbandonmentService:
    """Service handling patient queue abandonment, wait-time recalculation, and reporting."""

    def abandon_patient(
        self,
        token_identifier: str,
        reason: Optional[str] = None,
        recorded_by_user_id: Optional[str] = None,
    ) -> AbandonmentRecordResponse:
        """
        Flags a WAITING patient as ABANDONED upon departure.
        - Enforces that only WAITING patients can be abandoned.
        - Calculates elapsed wait time since check-in / token issuance.
        - Records an immutable timestamp event.
        - Automatically excludes the patient from the live queue.
        - Recalculates wait times for remaining waiting patients.
        """
        # 1. Lookup token by token_id or appointment_id in O(N) over memory dict or fetch from DB
        token = self._find_token(token_identifier)
        if not token:
            raise HTTPException(status_code=404, detail=f"Token '{token_identifier}' not found in queue")

        # 2. Acceptance Criteria 1 & Implementation Note 3:
        # Validate patient is currently in WAITING status
        if token.status != QueueStatus.WAITING:
            raise HTTPException(
                status_code=422,
                detail=f"Cannot abandon token '{token.token_number}' with status '{token.status.value}'. "
                       f"Only patients in 'Waiting' status can be marked as abandoned.",
            )

        now = datetime.now(timezone.utc)

        # 3. Acceptance Criteria 2: Calculate waiting duration elapsed
        # Check timestamp store for earlier token_issued or check_in reference
        wait_start_dt = self._resolve_wait_start_time(token)
        elapsed_seconds = max(0.0, (now - wait_start_dt).total_seconds())
        elapsed_minutes = round(elapsed_seconds / 60.0, 2)

        # 4. Acceptance Criteria 2: Immutably log abandonment event in timestamp store
        metadata = {
            "reason": reason,
            "waiting_duration_seconds": elapsed_seconds,
            "waiting_duration_minutes": elapsed_minutes,
            "doctor_id": token.doctor_id,
            "department_id": token.department_id,
        }
        record = OperationalTimestampRecord.create(
            token_id=token.token_id,
            patient_id=token.patient_id,
            stage=JourneyStage.ABANDONED,
            timestamp=now,
            appointment_id=token.appointment_id,
            doctor_id=token.doctor_id,
            department_id=token.department_id,
            recorded_by_user_id=recorded_by_user_id,
            notes=reason,
            metadata=metadata,
        )
        timestamp_store.append(record)

        # 5. Acceptance Criteria 3: Set status to ABANDONED (automatically removes from live queue)
        token.status = QueueStatus.ABANDONED

        # Persist status change to database if connected
        try:
            save_token({
                "token_id": token.token_id,
                "token_number": token.token_number,
                "appointment_id": token.appointment_id,
                "patient_id": token.patient_id,
                "status": token.status.value,
            })
        except Exception:
            pass

        # 6. Acceptance Criteria 4: Recalculate estimated wait times for remaining patients
        self._recalculate_remaining_wait_times(token.doctor_id, token.department_id)

        return AbandonmentRecordResponse(
            token=token,
            abandonment_time=now,
            waiting_duration_seconds=elapsed_seconds,
            waiting_duration_minutes=elapsed_minutes,
            reason=reason,
            recorded_by_user_id=recorded_by_user_id,
        )

    def get_abandonment_analytics(
        self,
        department_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
    ) -> AbandonmentAnalyticsResponse:
        """
        Acceptance Criteria 5 & 6:
        Aggregates abandonment rates and average waiting duration for management reporting.
        """
        abandoned_records = [
            r for r in timestamp_store.get_all()
            if r.stage == JourneyStage.ABANDONED
        ]

        if department_id:
            abandoned_records = [r for r in abandoned_records if r.department_id == department_id]
        if doctor_id:
            abandoned_records = [r for r in abandoned_records if r.doctor_id == doctor_id]

        total_abandoned = len(abandoned_records)
        all_tokens = list(queue_service_instance._tokens.values())
        if department_id:
            all_tokens = [t for t in all_tokens if t.department_id == department_id]
        if doctor_id:
            all_tokens = [t for t in all_tokens if t.doctor_id == doctor_id]

        total_tokens_count = max(len(all_tokens), total_abandoned)
        abandonment_rate = round((total_abandoned / total_tokens_count) * 100, 2) if total_tokens_count > 0 else 0.0

        durations: List[float] = []
        by_dept: Dict[str, int] = {}
        by_doc: Dict[str, int] = {}
        reasons: Dict[str, int] = {}

        for r in abandoned_records:
            wait_min = r.metadata.get("waiting_duration_minutes")
            if wait_min is not None:
                durations.append(wait_min)

            if r.department_id:
                by_dept[r.department_id] = by_dept.get(r.department_id, 0) + 1
            if r.doctor_id:
                by_doc[r.doctor_id] = by_doc.get(r.doctor_id, 0) + 1

            reason_text = r.notes or "Not specified"
            reasons[reason_text] = reasons.get(reason_text, 0) + 1

        avg_duration = round(sum(durations) / len(durations), 2) if durations else 0.0

        return AbandonmentAnalyticsResponse(
            total_tokens_tracked=total_tokens_count,
            total_abandoned=total_abandoned,
            abandonment_rate_pct=abandonment_rate,
            avg_waiting_duration_minutes=avg_duration,
            by_department=by_dept,
            by_doctor=by_doc,
            reasons_breakdown=reasons,
        )

    def _find_token(self, token_identifier: str) -> Optional[QueueToken]:
        """Finds token by token_id or appointment_id."""
        with queue_service_instance._lock:
            for t in queue_service_instance._tokens.values():
                if t.token_id == token_identifier or t.appointment_id == token_identifier:
                    return t
        # Fallback to database lookup via existing queue_service
        return queue_service_instance.get_token_by_appointment(token_identifier)

    def _resolve_wait_start_time(self, token: QueueToken) -> datetime:
        """Finds the earliest wait-start reference (token_issued, check_in, or queue_entry_time)."""
        history = timestamp_store.get_by_token(token.token_id)
        for h in history:
            if h.stage in (JourneyStage.TOKEN_ISSUED, JourneyStage.CHECK_IN):
                return h.timestamp

        entry = token.queue_entry_time
        if entry.tzinfo is None:
            return entry.replace(tzinfo=timezone.utc)
        return entry

    def _recalculate_remaining_wait_times(self, doctor_id: str, department_id: str):
        """
        Recalculates estimated wait times dynamically for remaining patients
        using real historical consultation averages via WaitingTimeService (HAQM-75).
        """
        from backend.services.queue.services.waiting_time_service import waiting_time_service_instance
        waiting_time_service_instance.recalculate_queue_wait_times(
            doctor_id=doctor_id,
            department_id=department_id,
        )


abandonment_service_instance = AbandonmentService()

