from datetime import datetime, timezone
from typing import Optional, Dict, List
from fastapi import HTTPException

from backend.services.queue.models.timestamp_models import (
    JourneyStage,
    OperationalTimestampRecord,
    timestamp_store,
)
from backend.services.queue.schemas.queue_schemas import QueueStatus, QueueToken
from backend.services.queue.schemas.no_show_schemas import (
    NoShowRecordResponse,
    NoShowAnalyticsResponse,
    PatientNoShowHistoryResponse,
)
from backend.services.queue.services.queue_service import queue_service_instance
from backend.database.token_fetcher import save_token


class NoShowService:
    """Service governing patient No-Show handling, patient profile logging, and reporting."""

    def mark_no_show(
        self,
        token_identifier: str,
        recorded_by_user_id: str,
        reason: Optional[str] = None,
    ) -> NoShowRecordResponse:
        """
        Marks a patient as No-Show when they fail to appear after being called.
        - Strict validation: patient must be in CALLED status (cannot be WAITING, IN_CONSULTATION, etc.).
        - Logs an immutable operational timestamp linked to recorded_by_user_id and patient profile.
        - Removes the patient from active queue sequence by updating status to NO_SHOW.
        """
        # 1. Lookup token by token_id or appointment_id in O(1)
        token = self._find_token(token_identifier)
        if not token:
            raise HTTPException(status_code=404, detail=f"Token '{token_identifier}' not found in queue")

        # 2. Acceptance Criteria 1:
        # Patient must be in CALLED status (unlike Abandonment which requires WAITING).
        if token.status != QueueStatus.CALLED:
            if token.status == QueueStatus.WAITING:
                raise HTTPException(
                    status_code=422,
                    detail=f"Cannot mark token '{token.token_number}' as No-Show while still in WAITING status. "
                           f"Patient must be called before they can be flagged as No-Show.",
                )
            raise HTTPException(
                status_code=422,
                detail=f"Cannot mark token '{token.token_number}' as No-Show with status '{token.status.value}'. "
                       f"Only patients in CALLED status who failed to appear can be marked as No-Show.",
            )

        now = datetime.now(timezone.utc)

        # 3. Acceptance Criteria 2 & 4: Immutably log event with recorded_by_user_id in timestamp store
        metadata = {
            "recorded_by_user_id": recorded_by_user_id,
            "reason": reason,
            "previous_status": token.status.value,
            "doctor_id": token.doctor_id,
            "department_id": token.department_id,
        }
        record = OperationalTimestampRecord.create(
            token_id=token.token_id,
            patient_id=token.patient_id,
            stage=JourneyStage.NO_SHOW,
            timestamp=now,
            appointment_id=token.appointment_id,
            doctor_id=token.doctor_id,
            department_id=token.department_id,
            recorded_by_user_id=recorded_by_user_id,
            notes=reason,
            metadata=metadata,
        )
        timestamp_store.append(record)

        # 4. Acceptance Criteria 2 & 3: Update status to NO_SHOW (removes from live queue)
        token.status = QueueStatus.NO_SHOW

        # HAQM-75: Recalculate remaining queue wait times dynamically
        try:
            from backend.services.queue.services.waiting_time_service import waiting_time_service_instance
            waiting_time_service_instance.recalculate_queue_wait_times(
                doctor_id=token.doctor_id,
                department_id=token.department_id,
            )
        except Exception:
            pass

        # Persist to database if connected
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

        return NoShowRecordResponse(
            token=token,
            no_show_time=now,
            recorded_by_user_id=recorded_by_user_id,
            reason=reason,
        )

    def get_no_show_analytics(
        self,
        department_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
    ) -> NoShowAnalyticsResponse:
        """
        Acceptance Criteria 4:
        Aggregates no-show metrics across doctors and departments for management reporting.
        """
        no_show_records = [
            r for r in timestamp_store.get_all()
            if r.stage == JourneyStage.NO_SHOW
        ]

        if department_id:
            no_show_records = [r for r in no_show_records if r.department_id == department_id]
        if doctor_id:
            no_show_records = [r for r in no_show_records if r.doctor_id == doctor_id]

        total_no_shows = len(no_show_records)
        all_tokens = list(queue_service_instance._tokens.values())
        if department_id:
            all_tokens = [t for t in all_tokens if t.department_id == department_id]
        if doctor_id:
            all_tokens = [t for t in all_tokens if t.doctor_id == doctor_id]

        total_tokens_count = max(len(all_tokens), total_no_shows)
        rate = round((total_no_shows / total_tokens_count) * 100, 2) if total_tokens_count > 0 else 0.0

        by_dept: Dict[str, int] = {}
        by_doc: Dict[str, int] = {}
        reasons: Dict[str, int] = {}

        for r in no_show_records:
            if r.department_id:
                by_dept[r.department_id] = by_dept.get(r.department_id, 0) + 1
            if r.doctor_id:
                by_doc[r.doctor_id] = by_doc.get(r.doctor_id, 0) + 1

            reason_text = r.notes or "Not specified"
            reasons[reason_text] = reasons.get(reason_text, 0) + 1

        return NoShowAnalyticsResponse(
            total_tokens_tracked=total_tokens_count,
            total_no_shows=total_no_shows,
            no_show_rate_pct=rate,
            by_department=by_dept,
            by_doctor=by_doc,
            reasons_breakdown=reasons,
        )

    def get_patient_no_show_history(self, patient_id: str) -> PatientNoShowHistoryResponse:
        """
        Acceptance Criteria 4:
        Retrieves all historical no-show logs for a specific patient profile.
        DSA: O(1) hash map lookup in timestamp_store._by_patient.
        """
        patient_records = [
            r for r in timestamp_store.get_by_patient(patient_id)
            if r.stage == JourneyStage.NO_SHOW
        ]

        history_items = [
            {
                "record_id": r.record_id,
                "token_id": r.token_id,
                "appointment_id": r.appointment_id,
                "doctor_id": r.doctor_id,
                "department_id": r.department_id,
                "timestamp": r.timestamp,
                "recorded_by_user_id": r.recorded_by_user_id,
                "reason": r.notes,
            }
            for r in patient_records
        ]

        return PatientNoShowHistoryResponse(
            patient_id=patient_id,
            total_no_shows=len(patient_records),
            records=history_items,
        )

    def _find_token(self, token_identifier: str) -> Optional[QueueToken]:
        with queue_service_instance._lock:
            for t in queue_service_instance._tokens.values():
                if t.token_id == token_identifier or t.appointment_id == token_identifier:
                    return t
        return queue_service_instance.get_token_by_appointment(token_identifier)


no_show_service_instance = NoShowService()
