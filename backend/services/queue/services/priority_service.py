from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException

from backend.services.queue.models.timestamp_models import (
    JourneyStage,
    OperationalTimestampRecord,
    timestamp_store,
)
from backend.services.queue.schemas.queue_schemas import QueuePriority, QueueToken
from backend.services.queue.schemas.priority_schemas import PriorityElevationResponse
from backend.services.queue.services.queue_service import queue_service_instance
from backend.services.queue.services.waiting_time_service import waiting_time_service_instance
from backend.database.token_fetcher import save_token


class PriorityService:
    """Service governing manual patient priority elevation, mandatory reason validation, and audit logging."""

    def elevate_priority(
        self,
        token_identifier: str,
        priority: QueuePriority,
        reason: str,
        recorded_by_user_id: str,
    ) -> PriorityElevationResponse:
        """
        Acceptance Criteria 3, 4, 5, 6:
        - Validates reason is non-empty (HTTP 422 if missing/blank).
        - Elevates token priority and populates visual badge metadata.
        - Records an immutable audit record in timestamp_store.
        - Triggers dynamic wait-time recalculation across the impacted queue.
        """
        # 1. Lookup token
        token = self._find_token(token_identifier)
        if not token:
            raise HTTPException(status_code=404, detail=f"Token '{token_identifier}' not found in queue")

        # 2. Acceptance Criteria 4: Mandatory reason validation
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=422,
                detail="A non-empty reason is required for manual priority elevation.",
            )

        cleaned_reason = reason.strip()
        old_priority_val = token.priority.value if hasattr(token.priority, "value") else str(token.priority)
        new_priority_val = priority.value if hasattr(priority, "value") else str(priority)
        now = datetime.now(timezone.utc)

        # 3. Acceptance Criteria 3 & 6: Update token priority and badge indicator fields
        with queue_service_instance._lock:
            token.priority = priority
            token.is_manually_elevated = True
            token.elevation_reason = cleaned_reason

        # 4. Acceptance Criteria 5: Record immutable audit record in timestamp_store
        metadata = {
            "action": "MANUAL_PRIORITY_ELEVATION",
            "previous_priority": old_priority_val,
            "new_priority": new_priority_val,
            "elevation_reason": cleaned_reason,
            "recorded_by_user_id": recorded_by_user_id,
            "doctor_id": token.doctor_id,
            "department_id": token.department_id,
        }

        audit_record = OperationalTimestampRecord.create(
            token_id=token.token_id,
            patient_id=token.patient_id,
            stage=JourneyStage.PRIORITY_ELEVATED,
            timestamp=now,
            appointment_id=token.appointment_id,
            doctor_id=token.doctor_id,
            department_id=token.department_id,
            recorded_by_user_id=recorded_by_user_id,
            notes=cleaned_reason,
            metadata=metadata,
        )
        timestamp_store.append(audit_record)

        # 5. Acceptance Criteria 2: Trigger wait time recalculation across queue
        waiting_time_service_instance.recalculate_queue_wait_times(
            doctor_id=token.doctor_id,
            department_id=token.department_id,
        )
        wait_info = waiting_time_service_instance.calculate_token_wait_time(token.token_id)
        token.estimated_wait_minutes = wait_info.estimated_wait_minutes

        # Persist to database if connected
        try:
            save_token({
                "token_id": token.token_id,
                "priority": new_priority_val,
                "estimated_wait_minutes": token.estimated_wait_minutes,
            })
        except Exception:
            pass

        return PriorityElevationResponse(
            token=token,
            previous_priority=old_priority_val,
            new_priority=new_priority_val,
            reason=cleaned_reason,
            recorded_by_user_id=recorded_by_user_id,
            elevated_at=now,
        )

    def _find_token(self, token_identifier: str) -> Optional[QueueToken]:
        with queue_service_instance._lock:
            for t in queue_service_instance._tokens.values():
                if t.token_id == token_identifier or t.appointment_id == token_identifier:
                    return t
        return queue_service_instance.get_token_by_appointment(token_identifier)


priority_service_instance = PriorityService()
