from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import HTTPException

from backend.services.queue.models.timestamp_models import (
    JourneyStage,
    OperationalTimestampRecord,
    TimestampStore,
    timestamp_store,
)
from backend.services.queue.schemas.timestamp_schemas import (
    TimestampRecordCreate,
    TimestampRecordResponse,
    TokenTimelineResponse,
    StageDurationMetrics,
    OperationalAnalyticsResponse,
)
from backend.services.queue.schemas.queue_schemas import QueueStatus
from backend.services.queue.services.queue_service import queue_service_instance


class TimestampService:
    """Service handling timestamp recording, journey sequence validation, and duration calculations."""

    def __init__(self, store: Optional[TimestampStore] = None):
        self.store = store or timestamp_store

    def record_timestamp(self, data: TimestampRecordCreate) -> TimestampRecordResponse:
        event_time = data.timestamp or datetime.now(timezone.utc)
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        # O(1) hash map lookup to get prior events for this token
        existing = self.store.get_by_token(data.token_id)

        # DSA: Use a hash set for O(1) membership checks on already recorded stages
        recorded_stages = {r.stage for r in existing}

        if data.stage in recorded_stages:
            raise HTTPException(
                status_code=422,
                detail=f"Stage '{data.stage.value}' has already been recorded for token '{data.token_id}'",
            )

        # Chronological check: the new event cannot be earlier than the most recent recorded event
        if existing and event_time < existing[-1].timestamp:
            latest = existing[-1]
            raise HTTPException(
                status_code=422,
                detail=f"Timestamp '{event_time.isoformat()}' cannot be earlier than previous stage "
                       f"'{latest.stage.value}' timestamp '{latest.timestamp.isoformat()}'",
            )

        # Business rule prerequisites:
        # 1. Cannot end consultation without starting it
        if data.stage == JourneyStage.CONSULTATION_END and JourneyStage.CONSULTATION_START not in recorded_stages:
            raise HTTPException(status_code=422, detail="Cannot end consultation before consultation has started")

        # 2. Cannot complete journey before consultation has occurred
        if data.stage == JourneyStage.COMPLETED and JourneyStage.CONSULTATION_START not in recorded_stages:
            raise HTTPException(status_code=422, detail="Cannot complete journey before consultation has occurred")

        # Create frozen record and append to store (immutable)
        record = OperationalTimestampRecord.create(
            token_id=data.token_id,
            patient_id=data.patient_id,
            stage=data.stage,
            timestamp=event_time,
            appointment_id=data.appointment_id,
            doctor_id=data.doctor_id,
            department_id=data.department_id,
            recorded_by_user_id=data.recorded_by_user_id,
            notes=data.notes,
            metadata=data.metadata,
        )
        saved = self.store.append(record)

        # Synchronize token status in live queue if appointment_id is provided
        if data.appointment_id:
            self._sync_queue_token(data.appointment_id, data.stage, event_time)

        return self._to_response(saved)

    def _sync_queue_token(self, appointment_id: str, stage: JourneyStage, event_time: datetime):
        """Synchronizes stage transition with existing QueueService live token state."""
        try:
            native_dt = event_time.replace(tzinfo=None)
            if stage == JourneyStage.CALLED:
                queue_service_instance.update_queue_status(appointment_id, QueueStatus.CALLED)
            elif stage == JourneyStage.CONSULTATION_START:
                queue_service_instance.update_queue_status(
                    appointment_id, QueueStatus.IN_CONSULTATION, consultation_start_time=native_dt
                )
            elif stage == JourneyStage.CONSULTATION_END:
                queue_service_instance.update_queue_status(
                    appointment_id, QueueStatus.COMPLETED, consultation_end_time=native_dt
                )
            elif stage == JourneyStage.COMPLETED:
                queue_service_instance.update_queue_status(appointment_id, QueueStatus.COMPLETED)
        except Exception:
            pass

    def get_token_timeline(self, token_id: str) -> TokenTimelineResponse:
        records = self.store.get_by_token(token_id)
        if not records:
            raise HTTPException(status_code=404, detail=f"No operational timestamps found for token '{token_id}'")

        metrics = self._calculate_metrics(records)
        is_completed = any(r.stage == JourneyStage.COMPLETED for r in records)

        return TokenTimelineResponse(
            token_id=token_id,
            patient_id=records[0].patient_id,
            current_stage=records[-1].stage.value,
            is_completed=is_completed,
            metrics=metrics,
            timeline=[self._to_response(r) for r in records],
        )

    def get_patient_history(self, patient_id: str) -> List[TimestampRecordResponse]:
        # O(1) hash map lookup for all records belonging to a patient
        records = self.store.get_by_patient(patient_id)
        return [self._to_response(r) for r in records]

    def get_operational_analytics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> OperationalAnalyticsResponse:
        records = self.store.get_all(start_time, end_time)

        # Group records by token_id using a dictionary (hash map)
        tokens_map: Dict[str, List[OperationalTimestampRecord]] = {}
        for r in records:
            tokens_map.setdefault(r.token_id, []).append(r)

        waiting_times: List[float] = []
        consultation_times: List[float] = []
        doctor_throughput: Dict[str, int] = {}
        stage_counts: Dict[str, int] = {}
        completed_count = 0

        for token_records in tokens_map.values():
            metrics = self._calculate_metrics(token_records)
            if metrics.waiting_time_minutes is not None:
                waiting_times.append(metrics.waiting_time_minutes)
            if metrics.consultation_duration_minutes is not None:
                consultation_times.append(metrics.consultation_duration_minutes)

            is_completed = any(r.stage == JourneyStage.COMPLETED for r in token_records)
            if is_completed:
                completed_count += 1
                for r in token_records:
                    if r.doctor_id:
                        doctor_throughput[r.doctor_id] = doctor_throughput.get(r.doctor_id, 0) + 1
                        break

            for r in token_records:
                stage_counts[r.stage.value] = stage_counts.get(r.stage.value, 0) + 1

        avg_wait = round(sum(waiting_times) / len(waiting_times), 2) if waiting_times else 0.0
        avg_consult = round(sum(consultation_times) / len(consultation_times), 2) if consultation_times else 0.0

        return OperationalAnalyticsResponse(
            total_tokens_tracked=len(tokens_map),
            completed_consultations=completed_count,
            avg_waiting_time_minutes=avg_wait,
            avg_consultation_time_minutes=avg_consult,
            doctor_throughput=doctor_throughput,
            stage_counts=stage_counts,
        )

    def _calculate_metrics(self, records: List[OperationalTimestampRecord]) -> StageDurationMetrics:
        # DSA: Map each stage to its timestamp for O(1) lookup during duration calculations
        stage_times = {r.stage: r.timestamp for r in records}
        intervals: Dict[str, float] = {}

        for i in range(len(records) - 1):
            curr_stage = records[i].stage.value
            next_stage = records[i + 1].stage.value
            diff = (records[i + 1].timestamp - records[i].timestamp).total_seconds()
            intervals[f"{curr_stage}_to_{next_stage}"] = max(0.0, diff)

        # 1. Waiting Time: token_issued (or check_in) -> consultation_start (or called)
        wait_seconds = None
        start_wait = stage_times.get(JourneyStage.TOKEN_ISSUED) or stage_times.get(JourneyStage.CHECK_IN)
        end_wait = stage_times.get(JourneyStage.CONSULTATION_START) or stage_times.get(JourneyStage.CALLED)
        if start_wait and end_wait and end_wait >= start_wait:
            wait_seconds = (end_wait - start_wait).total_seconds()

        # 2. Consultation Duration: consultation_start -> consultation_end
        consult_seconds = None
        c_start = stage_times.get(JourneyStage.CONSULTATION_START)
        c_end = stage_times.get(JourneyStage.CONSULTATION_END)
        if c_start and c_end and c_end >= c_start:
            consult_seconds = (c_end - c_start).total_seconds()

        # 3. Total Journey Duration: earliest event -> completed
        total_seconds = None
        c_completed = stage_times.get(JourneyStage.COMPLETED)
        if records and c_completed and c_completed >= records[0].timestamp:
            total_seconds = (c_completed - records[0].timestamp).total_seconds()

        return StageDurationMetrics(
            waiting_time_seconds=wait_seconds,
            waiting_time_minutes=round(wait_seconds / 60.0, 2) if wait_seconds is not None else None,
            consultation_duration_seconds=consult_seconds,
            consultation_duration_minutes=round(consult_seconds / 60.0, 2) if consult_seconds is not None else None,
            total_journey_duration_seconds=total_seconds,
            total_journey_duration_minutes=round(total_seconds / 60.0, 2) if total_seconds is not None else None,
            stage_intervals_seconds=intervals,
        )

    def _to_response(self, r: OperationalTimestampRecord) -> TimestampRecordResponse:
        return TimestampRecordResponse(
            record_id=r.record_id,
            token_id=r.token_id,
            patient_id=r.patient_id,
            stage=r.stage.value,
            timestamp=r.timestamp,
            appointment_id=r.appointment_id,
            doctor_id=r.doctor_id,
            department_id=r.department_id,
            recorded_by_user_id=r.recorded_by_user_id,
            notes=r.notes,
            metadata=r.metadata,
            created_at=r.created_at,
        )


timestamp_service = TimestampService()
