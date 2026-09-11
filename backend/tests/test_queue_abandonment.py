from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.queue.models.timestamp_models import (
    JourneyStage,
    timestamp_store,
)
from backend.services.queue.schemas.queue_schemas import QueuePriority, QueueStatus
from backend.services.queue.services.queue_service import queue_service_instance
from backend.services.queue.services.abandonment_service import abandonment_service_instance

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_queue_and_store():
    """Isolate tests by resetting in-memory queue tokens and timestamp store."""
    queue_service_instance._tokens.clear()
    queue_service_instance._token_counter = 100
    timestamp_store.clear()
    yield
    queue_service_instance._tokens.clear()
    timestamp_store.clear()


# =========================================================================
# 1. ACCEPTANCE CRITERIA: SUCCESSFULLY ABANDONING A WAITING PATIENT
# =========================================================================

def test_abandon_waiting_patient_successfully():
    """Verify that a waiting patient can be abandoned with reason and staff ID."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-ABANDON-1",
        patient_id="PAT-101",
        patient_name="John Doe",
        doctor_id="DOC-1",
        doctor_name="Dr. Smith",
        department_id="DEP-CARDIO",
        department_name="Cardiology",
    )

    response = client.patch(
        f"/api/queue/{token.token_id}/abandon",
        json={"reason": "Emergency personal issue", "recorded_by_user_id": "STAFF-01"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["token"]["status"] == "Abandoned"
    assert body["data"]["reason"] == "Emergency personal issue"
    assert body["data"]["recorded_by_user_id"] == "STAFF-01"
    assert body["data"]["waiting_duration_seconds"] >= 0

    # Verify immutable timestamp record exists in timestamp store
    history = timestamp_store.get_by_token(token.token_id)
    assert any(h.stage == JourneyStage.ABANDONED for h in history)


# =========================================================================
# 2. ACCEPTANCE CRITERIA: REJECTING ABANDONMENT OF NON-WAITING PATIENT
# =========================================================================

def test_reject_abandon_when_patient_not_in_waiting_status():
    """Verify abandonment is rejected if patient is CALLED or IN_CONSULTATION."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-CALLED-1",
        patient_id="PAT-102",
        patient_name="Alice Smith",
        doctor_id="DOC-1",
        doctor_name="Dr. Smith",
        department_id="DEP-CARDIO",
        department_name="Cardiology",
    )
    # Update status to Called
    queue_service_instance.update_queue_status(token.appointment_id, QueueStatus.CALLED)

    response = client.patch(
        f"/api/queue/{token.token_id}/abandon",
        json={"reason": "Tried to leave after being called"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "Only patients in 'Waiting' status can be marked as abandoned" in str(body["error"])


def test_reject_abandon_when_patient_already_completed():
    """Verify abandonment is rejected if consultation is already completed."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-COMPLETED-1",
        patient_id="PAT-103",
        patient_name="Bob Brown",
        doctor_id="DOC-1",
        doctor_name="Dr. Smith",
        department_id="DEP-CARDIO",
        department_name="Cardiology",
    )
    queue_service_instance.update_queue_status(token.appointment_id, QueueStatus.COMPLETED)

    response = client.patch(f"/api/queue/{token.token_id}/abandon", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False


# =========================================================================
# 3. ACCEPTANCE CRITERIA: WAITING DURATION CALCULATION & OPTIONAL REASON
# =========================================================================

def test_waiting_duration_calculation_accurate():
    """Verify waiting duration elapsed equals abandonment_time minus entry_time."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-DURATION-1",
        patient_id="PAT-104",
        patient_name="Charlie Davis",
        doctor_id="DOC-2",
        doctor_name="Dr. Adams",
        department_id="DEP-ORTHO",
        department_name="Orthopedics",
    )
    # Simulate entering queue 15 minutes ago
    ten_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=15)
    token.queue_entry_time = ten_mins_ago

    result = abandonment_service_instance.abandon_patient(
        token_identifier=token.token_id,
        reason=None,  # Optional reason omitted
        recorded_by_user_id="STAFF-02",
    )

    # 15 minutes = 900 seconds
    assert result.waiting_duration_minutes >= 14.9
    assert result.waiting_duration_seconds >= 890
    assert result.reason is None


# =========================================================================
# 4. ACCEPTANCE CRITERIA: REMOVAL FROM LIVE QUEUE & WAIT-TIME RECALCULATION
# =========================================================================

def test_removal_from_live_queue_and_wait_time_recalculation():
    """
    Verify:
    1. Patient is removed from GET /api/queue/live results.
    2. Remaining patients in that queue have their estimated wait times recalculated.
    """
    # Create 3 patients in Cardiology queue for Dr. Smith
    t1 = queue_service_instance.add_to_queue(
        appointment_id="APT-Q-1", patient_id="P1", patient_name="P1",
        doctor_id="DOC-CARDIO", doctor_name="Dr. Smith",
        department_id="DEP-CARDIO", department_name="Cardiology",
    )
    t2 = queue_service_instance.add_to_queue(
        appointment_id="APT-Q-2", patient_id="P2", patient_name="P2",
        doctor_id="DOC-CARDIO", doctor_name="Dr. Smith",
        department_id="DEP-CARDIO", department_name="Cardiology",
    )
    t3 = queue_service_instance.add_to_queue(
        appointment_id="APT-Q-3", patient_id="P3", patient_name="P3",
        doctor_id="DOC-CARDIO", doctor_name="Dr. Smith",
        department_id="DEP-CARDIO", department_name="Cardiology",
    )

    # Before abandonment: live queue has 3 tokens
    live_before = queue_service_instance.get_live_queue(doctor_id="DOC-CARDIO")
    assert len(live_before) == 3

    # Real wait time calculation (HAQM-75): (Patients Ahead) * 10 mins
    # Initial: T2 has 1 patient ahead (T1) -> 10 mins, T3 has 2 patients ahead (T1, T2) -> 20 mins
    assert t2.estimated_wait_minutes == 10
    assert t3.estimated_wait_minutes == 20

    # Abandon patient 1 (T1)
    client.patch(f"/api/queue/{t1.token_id}/abandon", json={"reason": "Left without waiting"})

    # Check live queue after abandonment: T1 must NOT be present
    live_after = client.get("/api/queue/live?doctor_id=DOC-CARDIO").json()["data"]
    assert len(live_after) == 2
    assert all(item["token_id"] != t1.token_id for item in live_after)

    # Check wait time recalculation for remaining patients:
    # T2 is now first in line (0 ahead) -> wait time reduced to 0 mins
    # T3 is now second in line (1 ahead) -> wait time reduced to 10 mins
    assert t2.estimated_wait_minutes == 0
    assert t3.estimated_wait_minutes == 10



# =========================================================================
# 5. ACCEPTANCE CRITERIA: ABANDONMENT ANALYTICS REPORTING
# =========================================================================

def test_abandonment_analytics_summary_endpoint():
    """Verify GET /api/queue/analytics/abandonment aggregates rates and elapsed times."""
    t1 = queue_service_instance.add_to_queue(
        appointment_id="APT-AN-1", patient_id="P-A", patient_name="A",
        doctor_id="DOC-1", doctor_name="Dr. A", department_id="DEP-1", department_name="D1"
    )
    t2 = queue_service_instance.add_to_queue(
        appointment_id="APT-AN-2", patient_id="P-B", patient_name="B",
        doctor_id="DOC-1", doctor_name="Dr. A", department_id="DEP-1", department_name="D1"
    )
    t3 = queue_service_instance.add_to_queue(
        appointment_id="APT-AN-3", patient_id="P-C", patient_name="C",
        doctor_id="DOC-2", doctor_name="Dr. B", department_id="DEP-2", department_name="D2"
    )

    # Abandon T1 and T3
    client.patch(f"/api/queue/{t1.token_id}/abandon", json={"reason": "Long wait"})
    client.patch(f"/api/queue/{t3.token_id}/abandon", json={"reason": "Emergency elsewhere"})

    res = client.get("/api/queue/analytics/abandonment")
    assert res.status_code == 200
    analytics = res.json()["data"]

    # 2 out of 3 tokens abandoned = 66.67%
    assert analytics["total_abandoned"] == 2
    assert analytics["total_tokens_tracked"] == 3
    assert analytics["abandonment_rate_pct"] == 66.67
    assert analytics["by_doctor"]["DOC-1"] == 1
    assert analytics["by_doctor"]["DOC-2"] == 1
    assert analytics["reasons_breakdown"]["Long wait"] == 1
    assert analytics["reasons_breakdown"]["Emergency elsewhere"] == 1
