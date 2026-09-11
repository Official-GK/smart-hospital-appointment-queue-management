from datetime import datetime, timezone
from typing import Optional, Dict, List
from fastapi import HTTPException

from backend.services.queue.models.timestamp_models import (
    JourneyStage,
    OperationalTimestampRecord,
    timestamp_store,
)
from backend.services.queue.models.doctor_workload_models import (
    DoctorAvailability,
    DoctorWorkloadRecord,
    doctor_workload_store,
)
from backend.services.queue.models.visit_history_models import (
    VisitRecord,
    visit_history_store,
)
from backend.services.queue.schemas.queue_schemas import QueueStatus, QueueToken
from backend.services.queue.schemas.completion_schemas import (
    CompletionRecordResponse,
    CompletedAnalyticsResponse,
    PatientVisitHistoryResponse,
    DoctorWorkloadResponse,
)
from backend.services.queue.services.queue_service import queue_service_instance
from backend.database.token_fetcher import save_token


class CompletionService:
    """Service governing consultation conclusion, visit archiving, and doctor workload updates."""

    def complete_consultation(
        self,
        token_identifier: str,
        recorded_by_user_id: str,
        notes: Optional[str] = None,
    ) -> CompletionRecordResponse:
        """
        Acceptance Criteria 1, 2, 3, 4:
        - Strict validation: Patient must be in IN_CONSULTATION status.
        - Records consultation_end & completed operational timestamps.
        - Computes exact consultation duration (start -> end).
        - Transitions token status to COMPLETED (removing from active live queue).
        - Archives record into VisitHistoryStore.
        - Updates doctor workload metrics and resets doctor availability to AVAILABLE.
        """
        # 1. Lookup token by token_id or appointment_id
        token = self._find_token(token_identifier)
        if not token:
            raise HTTPException(status_code=404, detail=f"Token '{token_identifier}' not found in queue")

        # 2. Strict Status Validation: Must be IN_CONSULTATION
        if token.status != QueueStatus.IN_CONSULTATION:
            raise HTTPException(
                status_code=422,
                detail=f"Cannot end consultation for token '{token.token_number}' with status '{token.status.value}'. "
                       f"Only patients in 'In Consultation' status can be marked as Completed.",
            )

        now = datetime.now(timezone.utc)

        # 3. Determine consultation start time
        start_time = token.consultation_start_time
        if not start_time:
            # Check timestamp store records for CONSULTATION_START
            token_records = timestamp_store.get_by_token(token.token_id)
            c_start_record = next((r for r in token_records if r.stage == JourneyStage.CONSULTATION_START), None)
            if c_start_record:
                start_time = c_start_record.timestamp
            else:
                start_time = token.called_time or token.queue_entry_time or now

        # Ensure start_time has timezone for duration subtraction
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        duration_seconds = max(0.0, (now - start_time).total_seconds())
        duration_minutes = round(duration_seconds / 60.0, 2)

        # 4. Acceptance Criteria 2: Log immutable operational timestamps
        metadata = {
            "recorded_by_user_id": recorded_by_user_id,
            "consultation_duration_seconds": duration_seconds,
            "consultation_duration_minutes": duration_minutes,
            "doctor_id": token.doctor_id,
            "department_id": token.department_id,
        }

        # Stage: CONSULTATION_END
        end_record = OperationalTimestampRecord.create(
            token_id=token.token_id,
            patient_id=token.patient_id,
            stage=JourneyStage.CONSULTATION_END,
            timestamp=now,
            appointment_id=token.appointment_id,
            doctor_id=token.doctor_id,
            department_id=token.department_id,
            recorded_by_user_id=recorded_by_user_id,
            notes=notes,
            metadata=metadata,
        )
        timestamp_store.append(end_record)

        # Stage: COMPLETED
        complete_record = OperationalTimestampRecord.create(
            token_id=token.token_id,
            patient_id=token.patient_id,
            stage=JourneyStage.COMPLETED,
            timestamp=now,
            appointment_id=token.appointment_id,
            doctor_id=token.doctor_id,
            department_id=token.department_id,
            recorded_by_user_id=recorded_by_user_id,
            notes=notes,
            metadata=metadata,
        )
        timestamp_store.append(complete_record)

        # 5. Acceptance Criteria 1 & 3: Update Token State to COMPLETED
        token.consultation_end_time = now
        token.status = QueueStatus.COMPLETED

        # 6. Acceptance Criteria 3: Archive to VisitHistoryStore
        visit_record = VisitRecord.create(
            token_id=token.token_id,
            appointment_id=token.appointment_id,
            patient_id=token.patient_id,
            patient_name=token.patient_name,
            doctor_id=token.doctor_id,
            doctor_name=token.doctor_name,
            department_id=token.department_id,
            department_name=token.department_name,
            consultation_start_time=start_time,
            consultation_end_time=now,
            duration_seconds=duration_seconds,
            recorded_by_user_id=recorded_by_user_id,
            notes=notes,
        )
        visit_history_store.append(visit_record)

        # 7. Acceptance Criteria 4: Update Doctor Workload & Reset Availability to AVAILABLE
        doc_record = doctor_workload_store.mark_completed_and_available(
            doctor_id=token.doctor_id,
            doctor_name=token.doctor_name,
            duration_seconds=duration_seconds,
        )

        # 8. HAQM-75: Recalculate remaining queue wait times dynamically
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
                "consultation_end_time": now.isoformat(),
            })
        except Exception:
            pass

        return CompletionRecordResponse(
            token=token,
            consultation_duration_seconds=duration_seconds,
            consultation_duration_minutes=duration_minutes,
            archived_visit_id=visit_record.visit_id,
            doctor_availability=doc_record.availability.value,
            recorded_by_user_id=recorded_by_user_id,
            notes=notes,
        )

    def get_completion_analytics(
        self,
        department_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
    ) -> CompletedAnalyticsResponse:
        """
        Aggregates consultation completion metrics across departments and doctors.
        """
        visits = visit_history_store.get_all()
        if department_id:
            visits = [v for v in visits if v.department_id == department_id]
        if doctor_id:
            visits = [v for v in visits if v.doctor_id == doctor_id]

        total_completed = len(visits)
        total_sec = sum(v.duration_seconds for v in visits)
        avg_sec = round(total_sec / total_completed, 2) if total_completed > 0 else 0.0
        avg_min = round(avg_sec / 60.0, 2) if total_completed > 0 else 0.0

        by_dept: Dict[str, int] = {}
        by_doc: Dict[str, int] = {}
        for v in visits:
            if v.department_id:
                by_dept[v.department_id] = by_dept.get(v.department_id, 0) + 1
            if v.doctor_id:
                by_doc[v.doctor_id] = by_doc.get(v.doctor_id, 0) + 1

        return CompletedAnalyticsResponse(
            total_completed=total_completed,
            average_duration_seconds=avg_sec,
            average_duration_minutes=avg_min,
            by_department=by_dept,
            by_doctor=by_doc,
        )

    def get_patient_visits(self, patient_id: str) -> PatientVisitHistoryResponse:
        """
        Retrieves archived visit records for a patient profile.
        """
        patient_visits = visit_history_store.get_by_patient(patient_id)
        visit_items = [
            {
                "visit_id": v.visit_id,
                "token_id": v.token_id,
                "appointment_id": v.appointment_id,
                "doctor_id": v.doctor_id,
                "doctor_name": v.doctor_name,
                "department_id": v.department_id,
                "department_name": v.department_name,
                "consultation_start_time": v.consultation_start_time,
                "consultation_end_time": v.consultation_end_time,
                "duration_seconds": v.duration_seconds,
                "duration_minutes": v.duration_minutes,
                "recorded_by_user_id": v.recorded_by_user_id,
                "notes": v.notes,
                "completed_at": v.completed_at,
            }
            for v in patient_visits
        ]
        return PatientVisitHistoryResponse(
            patient_id=patient_id,
            total_visits=len(patient_visits),
            visits=visit_items,
        )

    def get_doctor_workload(self, doctor_id: str) -> DoctorWorkloadResponse:
        """
        Retrieves current workload and availability status for a doctor.
        """
        record = doctor_workload_store.get_doctor_workload(doctor_id)
        if not record:
            return DoctorWorkloadResponse(
                doctor_id=doctor_id,
                doctor_name="Unknown",
                availability=DoctorAvailability.AVAILABLE.value,
                completed_consultations_count=0,
                total_consultation_seconds=0.0,
            )
        return DoctorWorkloadResponse(
            doctor_id=record.doctor_id,
            doctor_name=record.doctor_name,
            availability=record.availability.value,
            completed_consultations_count=record.completed_consultations_count,
            total_consultation_seconds=record.total_consultation_seconds,
            last_completed_at=record.last_completed_at,
        )

    def _find_token(self, token_identifier: str) -> Optional[QueueToken]:
        with queue_service_instance._lock:
            for t in queue_service_instance._tokens.values():
                if t.token_id == token_identifier or t.appointment_id == token_identifier:
                    return t
        return queue_service_instance.get_token_by_appointment(token_identifier)


completion_service_instance = CompletionService()
