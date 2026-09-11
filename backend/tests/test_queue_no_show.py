import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.queue.models.timestamp_models import (
    JourneyStage,
    timestamp_store,
)
from backend.services.queue.schemas.queue_schemas import QueueStatus
from backend.services.queue.services.queue_service import queue_service_instance
from backend.services.queue.services.no_show_service import no_show_service_instance

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_queue_and_store():
    """Isolate tests by clearing in-memory queue tokens and timestamp store."""
    queue_service_instance._tokens.clear()
    queue_service_instance._token_counter = 100
    timestamp_store.clear()
    yield
    queue_service_instance._tokens.clear()
    timestamp_store.clear()


# =========================================================================
# 1. ACCEPTANCE CRITERIA: SUCCESSFULLY MARKING A CALLED PATIENT AS NO-SHOW
# =========================================================================

def test_mark_called_patient_no_show_successfully():
    """Verify that a patient in CALLED status can be marked as No-Show with recorded_by_user_id."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-NS-01",
        patient_id="PAT-201",
        patient_name="Michael Scott",
        doctor_id="DOC-CARDIO",
        doctor_name="Dr. House",
        department_id="DEP-CARDIO",
        department_name="Cardiology",
    )
    # Advance status to CALLED (prerequisite for No-Show)
    token.status = QueueStatus.CALLED

    response = client.patch(
        f"/api/queue/{token.token_id}/no-show",
        json={"recorded_by_user_id": "STAFF-NURSE-01", "reason": "Did not appear after 3 PA calls"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["token"]["status"] == "No-Show"
    assert body["data"]["recorded_by_user_id"] == "STAFF-NURSE-01"
    assert body["data"]["reason"] == "Did not appear after 3 PA calls"

    # Verify immutable timestamp logging in store with correct stage and user id
    history = timestamp_store.get_by_token(token.token_id)
    assert any(h.stage == JourneyStage.NO_SHOW for h in history)
    no_show_record = [h for h in history if h.stage == JourneyStage.NO_SHOW][0]
    assert no_show_record.recorded_by_user_id == "STAFF-NURSE-01"
    assert no_show_record.patient_id == "PAT-201"


def test_mark_called_patient_no_show_without_optional_reason():
    """Verify marking No-Show works with only recorded_by_user_id (reason is optional)."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-NS-02",
        patient_id="PAT-202",
        patient_name="Pam Beesly",
        doctor_id="DOC-ORTHO",
        doctor_name="Dr. Bones",
        department_id="DEP-ORTHO",
        department_name="Orthopedics",
    )
    token.status = QueueStatus.CALLED

    response = client.patch(
        f"/api/queue/{token.token_id}/no-show",
        json={"recorded_by_user_id": "DOC-ORTHO"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["token"]["status"] == "No-Show"
    assert body["data"]["recorded_by_user_id"] == "DOC-ORTHO"


# =========================================================================
# 2. ACCEPTANCE CRITERIA: REJECTING NO-SHOW ON WAITING PATIENTS (KEY DIFFERENCE)
# =========================================================================

def test_reject_no_show_attempt_on_waiting_patient():
    """
    Key difference from HAQM-81 (Abandonment):
    A patient in WAITING status CANNOT be marked as No-Show.
    They must be called first.
    """
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-NS-WAIT-1",
        patient_id="PAT-203",
        patient_name="Jim Halpert",
        doctor_id="DOC-CARDIO",
        doctor_name="Dr. House",
        department_id="DEP-CARDIO",
        department_name="Cardiology",
    )
    assert token.status == QueueStatus.WAITING

    response = client.patch(
        f"/api/queue/{token.token_id}/no-show",
        json={"recorded_by_user_id": "STAFF-01"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "WAITING status" in str(body["error"]) or "Patient must be called before" in str(body["error"])


# =========================================================================
# 3. ACCEPTANCE CRITERIA: REJECTING NO-SHOW ON COMPLETED OR ABANDONED PATIENTS
# =========================================================================

def test_reject_no_show_when_in_consultation_completed_or_abandoned():
    """Verify rejection when patient is in IN_CONSULTATION, COMPLETED, or ABANDONED status."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-NS-INVALID-1",
        patient_id="PAT-204",
        patient_name="Dwight Schrute",
        doctor_id="DOC-CARDIO",
        doctor_name="Dr. House",
        department_id="DEP-CARDIO",
        department_name="Cardiology",
    )

    # 1. In consultation
    token.status = QueueStatus.IN_CONSULTATION
    res_in_consult = client.patch(
        f"/api/queue/{token.token_id}/no-show",
        json={"recorded_by_user_id": "STAFF-01"},
    )
    assert res_in_consult.status_code == 422

    # 2. Completed
    token.status = QueueStatus.COMPLETED
    res_completed = client.patch(
        f"/api/queue/{token.token_id}/no-show",
        json={"recorded_by_user_id": "STAFF-01"},
    )
    assert res_completed.status_code == 422

    # 3. Abandoned
    token.status = QueueStatus.ABANDONED
    res_abandoned = client.patch(
        f"/api/queue/{token.token_id}/no-show",
        json={"recorded_by_user_id": "STAFF-01"},
    )
    assert res_abandoned.status_code == 422


# =========================================================================
# 4. ACCEPTANCE CRITERIA: REMOVED FROM ACTIVE QUEUE SO NEXT PATIENT CAN BE CALLED
# =========================================================================

def test_removal_from_active_queue_allows_next_patient():
    """Verify marking No-Show removes token from live queue, allowing next waiting patient to proceed."""
    token1 = queue_service_instance.add_to_queue(
        appointment_id="APT-NS-ACTIVE-1",
        patient_id="PAT-301",
        patient_name="Patient First",
        doctor_id="DOC-1",
        doctor_name="Dr. Doctor",
        department_id="DEP-GEN",
        department_name="General Medicine",
    )
    token2 = queue_service_instance.add_to_queue(
        appointment_id="APT-NS-ACTIVE-2",
        patient_id="PAT-302",
        patient_name="Patient Next",
        doctor_id="DOC-1",
        doctor_name="Dr. Doctor",
        department_id="DEP-GEN",
        department_name="General Medicine",
    )

    # Call token1
    token1.status = QueueStatus.CALLED

    # Active live queue shows both token1 (CALLED) and token2 (WAITING)
    live_res = client.get("/api/queue/live")
    live_tokens = live_res.json()["data"]
    live_ids = [t["token_id"] for t in live_tokens]
    assert token1.token_id in live_ids
    assert token2.token_id in live_ids

    # Mark token1 as No-Show
    client.patch(
        f"/api/queue/{token1.token_id}/no-show",
        json={"recorded_by_user_id": "NURSE-DESK-1"},
    )

    # Active queue now excludes token1; token2 is now next in line to be called
    live_res_after = client.get("/api/queue/live")
    remaining_ids = [t["token_id"] for t in live_res_after.json()["data"]]
    assert token1.token_id not in remaining_ids
    assert token2.token_id in remaining_ids

    # Doctor can now call token2
    token2.status = QueueStatus.CALLED
    assert token2.status == QueueStatus.CALLED


# =========================================================================
# 5. ACCEPTANCE CRITERIA: OPERATIONAL ANALYTICS & PATIENT PROFILE LOGGING
# =========================================================================

def test_no_show_analytics_aggregation():
    """Verify aggregated metrics (total tracked, no-shows, rates, department/doctor breakdowns)."""
    # 1. Token in Cardio -> CALLED -> No Show
    t1 = queue_service_instance.add_to_queue(
        appointment_id="APT-AN-1",
        patient_id="PAT-401",
        patient_name="Cardio Patient",
        doctor_id="DOC-CARDIO",
        doctor_name="Dr. Heart",
        department_id="DEP-CARDIO",
        department_name="Cardiology",
    )
    t1.status = QueueStatus.CALLED
    client.patch(f"/api/queue/{t1.token_id}/no-show", json={"recorded_by_user_id": "STAFF-1", "reason": "Late arrival"})

    # 2. Token in Ortho -> CALLED -> No Show
    t2 = queue_service_instance.add_to_queue(
        appointment_id="APT-AN-2",
        patient_id="PAT-402",
        patient_name="Ortho Patient",
        doctor_id="DOC-ORTHO",
        doctor_name="Dr. Bone",
        department_id="DEP-ORTHO",
        department_name="Orthopedics",
    )
    t2.status = QueueStatus.CALLED
    client.patch(f"/api/queue/{t2.token_id}/no-show", json={"recorded_by_user_id": "STAFF-2", "reason": "Unreachable"})

    # 3. Token in Cardio -> Normal Waiting (Active)
    queue_service_instance.add_to_queue(
        appointment_id="APT-AN-3",
        patient_id="PAT-403",
        patient_name="Active Waiting Patient",
        doctor_id="DOC-CARDIO",
        doctor_name="Dr. Heart",
        department_id="DEP-CARDIO",
        department_name="Cardiology",
    )

    analytics_res = client.get("/api/queue/analytics/no-show")
    assert analytics_res.status_code == 200
    data = analytics_res.json()["data"]

    assert data["total_tokens_tracked"] == 3
    assert data["total_no_shows"] == 2
    assert data["no_show_rate_pct"] == round((2 / 3) * 100, 2)
    assert data["by_department"]["DEP-CARDIO"] == 1
    assert data["by_department"]["DEP-ORTHO"] == 1
    assert data["reasons_breakdown"]["Late arrival"] == 1
    assert data["reasons_breakdown"]["Unreachable"] == 1

    # Filtered by department query
    filtered_res = client.get("/api/queue/analytics/no-show?department_id=DEP-CARDIO")
    filtered_data = filtered_res.json()["data"]
    assert filtered_data["total_no_shows"] == 1
    assert "DEP-CARDIO" in filtered_data["by_department"]


def test_patient_no_show_profile_history():
    """Verify no-show event is logged in patient profile for reliability reporting."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-NS-06",
        patient_id="PAT-RELIABILITY-99",
        patient_name="Stanley Hudson",
        doctor_id="DOC-1",
        doctor_name="Dr. Doctor",
        department_id="DEP-GEN",
        department_name="General Medicine",
    )
    token.status = QueueStatus.CALLED

    client.patch(
        f"/api/queue/{token.token_id}/no-show",
        json={"recorded_by_user_id": "STAFF-09", "reason": "Refused to respond to buzzer"},
    )

    history_res = client.get(f"/api/queue/patients/PAT-RELIABILITY-99/no-shows")
    assert history_res.status_code == 200
    body = history_res.json()
    assert body["success"] is True
    assert body["data"]["patient_id"] == "PAT-RELIABILITY-99"
    assert body["data"]["total_no_shows"] == 1
    assert len(body["data"]["records"]) == 1
    assert body["data"]["records"][0]["recorded_by_user_id"] == "STAFF-09"
    assert body["data"]["records"][0]["reason"] == "Refused to respond to buzzer"
