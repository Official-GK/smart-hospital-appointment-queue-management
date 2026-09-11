from datetime import datetime, timezone, timedelta
import pytest
from dataclasses import FrozenInstanceError
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.queue.models.timestamp_models import (
    JourneyStage,
    OperationalTimestampRecord,
    timestamp_store,
)
from backend.services.queue.schemas.timestamp_schemas import TimestampRecordCreate
from backend.services.queue.services.timestamp_service import timestamp_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    """Reset the timestamp store before and after every test."""
    timestamp_store.clear()
    yield
    timestamp_store.clear()


# =========================================================================
# 1. ACCEPTANCE CRITERIA: CAPTURE TIMESTAMPS AT ALL 8 JOURNEY STAGES
# =========================================================================

def test_capture_all_eight_journey_stages_successfully():
    """Verify timestamps are accurately recorded across all 8 mandatory patient journey stages."""
    token_id = "TOK-101"
    patient_id = "PAT-202"
    base_time = datetime(2026, 9, 11, 9, 0, 0, tzinfo=timezone.utc)

    stages = [
        (JourneyStage.REGISTRATION, base_time),
        (JourneyStage.BOOKING, base_time + timedelta(minutes=5)),
        (JourneyStage.CHECK_IN, base_time + timedelta(minutes=15)),
        (JourneyStage.TOKEN_ISSUED, base_time + timedelta(minutes=16)),
        (JourneyStage.CALLED, base_time + timedelta(minutes=30)),
        (JourneyStage.CONSULTATION_START, base_time + timedelta(minutes=32)),
        (JourneyStage.CONSULTATION_END, base_time + timedelta(minutes=47)),
        (JourneyStage.COMPLETED, base_time + timedelta(minutes=50)),
    ]

    for stage, event_time in stages:
        create_payload = TimestampRecordCreate(
            token_id=token_id,
            patient_id=patient_id,
            stage=stage,
            timestamp=event_time,
            doctor_id="DOC-1",
            department_id="CARDIO",
            recorded_by_user_id="STAFF-1",
        )
        record = timestamp_service.record_timestamp(create_payload)
        assert record.token_id == token_id
        assert record.stage == stage.value
        assert record.timestamp == event_time
        assert record.record_id is not None

    timeline = timestamp_service.get_token_timeline(token_id)
    assert len(timeline.timeline) == 8
    assert timeline.is_completed is True
    assert timeline.current_stage == JourneyStage.COMPLETED.value


# =========================================================================
# 2. ACCEPTANCE CRITERIA: IMMUTABILITY OF RECORDS
# =========================================================================

def test_record_immutability_attribute_modification_fails():
    """Verify that domain records are frozen and cannot be tampered with or modified."""
    record = OperationalTimestampRecord.create(
        token_id="TOK-IMMUTABLE",
        patient_id="PAT-IMMUTABLE",
        stage=JourneyStage.CHECK_IN,
    )
    timestamp_store.append(record)

    with pytest.raises(FrozenInstanceError):
        record.stage = JourneyStage.COMPLETED  # type: ignore

    with pytest.raises(FrozenInstanceError):
        record.timestamp = datetime.now(timezone.utc)  # type: ignore


def test_prevent_duplicate_stage_capture():
    """Verify that the exact same stage cannot be recorded multiple times for the same token."""
    from fastapi import HTTPException
    create_payload = TimestampRecordCreate(
        token_id="TOK-DUP",
        patient_id="PAT-DUP",
        stage=JourneyStage.CHECK_IN,
    )
    timestamp_service.record_timestamp(create_payload)

    with pytest.raises(HTTPException) as exc_info:
        timestamp_service.record_timestamp(create_payload)

    assert exc_info.value.status_code == 422
    assert "already been recorded" in str(exc_info.value.detail)


# =========================================================================
# 3. ACCEPTANCE CRITERIA: CHRONOLOGICAL INTEGRITY & VALIDATION
# =========================================================================

def test_reject_reverse_chronological_timestamp():
    """Verify that stage timestamps cannot precede prior stage timestamps."""
    from fastapi import HTTPException
    t1 = datetime(2026, 9, 11, 10, 0, 0, tzinfo=timezone.utc)
    t2_earlier = datetime(2026, 9, 11, 9, 50, 0, tzinfo=timezone.utc)

    timestamp_service.record_timestamp(
        TimestampRecordCreate(token_id="TOK-TIME", patient_id="PAT-TIME", stage=JourneyStage.CHECK_IN, timestamp=t1)
    )

    with pytest.raises(HTTPException) as exc_info:
        timestamp_service.record_timestamp(
            TimestampRecordCreate(token_id="TOK-TIME", patient_id="PAT-TIME", stage=JourneyStage.CALLED, timestamp=t2_earlier)
        )

    assert exc_info.value.status_code == 422
    assert "cannot be earlier than previous stage" in str(exc_info.value.detail)


def test_reject_consultation_end_before_start():
    """Verify consultation_end is rejected if consultation_start was never logged."""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        timestamp_service.record_timestamp(
            TimestampRecordCreate(token_id="TOK-ORDER", patient_id="PAT-ORDER", stage=JourneyStage.CONSULTATION_END)
        )

    assert exc_info.value.status_code == 422
    assert "Cannot end consultation before consultation has started" in str(exc_info.value.detail)


# =========================================================================
# 4. ACCEPTANCE CRITERIA: DURATION METRICS BASELINE
# =========================================================================

def test_baseline_duration_metrics_computation():
    """
    Verify accurate calculation of:
    - Waiting time: token_issued -> consultation_start
    - Consultation duration: consultation_start -> consultation_end
    - Total turnaround: check_in -> completed
    """
    token_id = "TOK-METRICS"
    t_check_in = datetime(2026, 9, 11, 10, 0, 0, tzinfo=timezone.utc)
    t_issued = datetime(2026, 9, 11, 10, 2, 0, tzinfo=timezone.utc)
    t_consult_start = datetime(2026, 9, 11, 10, 22, 0, tzinfo=timezone.utc)  # 20 min wait
    t_consult_end = datetime(2026, 9, 11, 10, 37, 0, tzinfo=timezone.utc)    # 15 min consultation
    t_completed = datetime(2026, 9, 11, 10, 40, 0, tzinfo=timezone.utc)      # 40 min total

    for stage, t in [
        (JourneyStage.CHECK_IN, t_check_in),
        (JourneyStage.TOKEN_ISSUED, t_issued),
        (JourneyStage.CONSULTATION_START, t_consult_start),
        (JourneyStage.CONSULTATION_END, t_consult_end),
        (JourneyStage.COMPLETED, t_completed),
    ]:
        timestamp_service.record_timestamp(
            TimestampRecordCreate(token_id=token_id, patient_id="PAT-1", stage=stage, timestamp=t)
        )

    timeline = timestamp_service.get_token_timeline(token_id)
    metrics = timeline.metrics

    # Waiting time: 10:22 - 10:02 = 20 min = 1200 sec
    assert metrics.waiting_time_seconds == 1200.0
    assert metrics.waiting_time_minutes == 20.0

    # Consultation duration: 10:37 - 10:22 = 15 min = 900 sec
    assert metrics.consultation_duration_seconds == 900.0
    assert metrics.consultation_duration_minutes == 15.0

    # Total turnaround: 10:40 - 10:00 = 40 min = 2400 sec
    assert metrics.total_journey_duration_seconds == 2400.0
    assert metrics.total_journey_duration_minutes == 40.0


# =========================================================================
# 5. ACCEPTANCE CRITERIA: OPERATIONAL REPORTING & DASHBOARD ANALYTICS
# =========================================================================

def test_operational_reporting_analytics_summary():
    """Verify aggregated metrics for management dashboards across multiple patients and doctors."""
    t0 = datetime(2026, 9, 11, 9, 0, 0, tzinfo=timezone.utc)
    for stage, dt in [
        (JourneyStage.TOKEN_ISSUED, 0),
        (JourneyStage.CONSULTATION_START, 10),
        (JourneyStage.CONSULTATION_END, 20),
        (JourneyStage.COMPLETED, 22),
    ]:
        timestamp_service.record_timestamp(
            TimestampRecordCreate(
                token_id="T1", patient_id="P1", stage=stage,
                timestamp=t0 + timedelta(minutes=dt), doctor_id="DOC-A"
            )
        )

    for stage, dt in [
        (JourneyStage.TOKEN_ISSUED, 0),
        (JourneyStage.CONSULTATION_START, 20),
        (JourneyStage.CONSULTATION_END, 40),
        (JourneyStage.COMPLETED, 42),
    ]:
        timestamp_service.record_timestamp(
            TimestampRecordCreate(
                token_id="T2", patient_id="P2", stage=stage,
                timestamp=t0 + timedelta(minutes=dt), doctor_id="DOC-B"
            )
        )

    analytics = timestamp_service.get_operational_analytics()
    assert analytics.total_tokens_tracked == 2
    assert analytics.completed_consultations == 2
    assert analytics.avg_waiting_time_minutes == 15.0
    assert analytics.avg_consultation_time_minutes == 15.0
    assert analytics.doctor_throughput.get("DOC-A") == 1
    assert analytics.doctor_throughput.get("DOC-B") == 1


# =========================================================================
# 6. REST API INTEGRATION TESTS
# =========================================================================

def test_api_record_timestamp_and_get_timeline():
    """Verify REST API recording and timeline retrieval via FastAPI client."""
    payload = {
        "token_id": "TOK-REST-1",
        "patient_id": "PAT-REST-1",
        "stage": "check_in",
        "doctor_id": "DOC-5",
        "department_id": "Cardiology",
    }
    response = client.post("/api/queue/timestamps", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["token_id"] == "TOK-REST-1"
    assert body["data"]["stage"] == "check_in"

    # Get timeline
    timeline_res = client.get("/api/queue/timestamps/token/TOK-REST-1")
    assert timeline_res.status_code == 200
    timeline_body = timeline_res.json()
    assert timeline_body["success"] is True
    assert len(timeline_body["data"]["timeline"]) == 1

    # Analytics summary
    analytics_res = client.get("/api/queue/timestamps/analytics/summary")
    assert analytics_res.status_code == 200
    analytics_body = analytics_res.json()
    assert analytics_body["success"] is True
    assert analytics_body["data"]["total_tokens_tracked"] == 1
