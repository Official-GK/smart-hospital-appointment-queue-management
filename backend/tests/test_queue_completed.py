from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.queue.models.timestamp_models import (
    JourneyStage,
    timestamp_store,
)
from backend.services.queue.models.doctor_workload_models import (
    DoctorAvailability,
    doctor_workload_store,
)
from backend.services.queue.models.visit_history_models import (
    visit_history_store,
)
from backend.services.queue.schemas.queue_schemas import QueueStatus
from backend.services.queue.services.queue_service import queue_service_instance

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_all_stores():
    """Isolate tests by clearing in-memory queue tokens, timestamps, visits, and doctor workloads."""
    queue_service_instance._tokens.clear()
    queue_service_instance._token_counter = 100
    timestamp_store.clear()
    visit_history_store.clear()
    doctor_workload_store.clear()
    yield
    queue_service_instance._tokens.clear()
    timestamp_store.clear()
    visit_history_store.clear()
    doctor_workload_store.clear()


# =========================================================================
# 1. ACCEPTANCE CRITERIA: SUCCESSFULLY COMPLETE IN_CONSULTATION PATIENT
# =========================================================================

def test_complete_in_consultation_patient_successfully():
    """Verify that an IN_CONSULTATION patient can be completed with duration calculation."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-CMP-01",
        patient_id="PAT-501",
        patient_name="Jim Halpert",
        doctor_id="DOC-CARDIO-1",
        doctor_name="Dr. Heart",
        department_id="DEP-CARDIO",
        department_name="Cardiology",
    )
    # Transition to IN_CONSULTATION 15 minutes in the past
    start_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    token.status = QueueStatus.IN_CONSULTATION
    token.consultation_start_time = start_time
    doctor_workload_store.set_busy("DOC-CARDIO-1", "Dr. Heart", token.token_id)

    response = client.patch(
        f"/api/queue/{token.token_id}/complete",
        json={"recorded_by_user_id": "DOC-CARDIO-1", "notes": "Checkup successful, vitals normal"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]

    # Status updated to Completed
    assert data["token"]["status"] == "Completed"
    assert data["recorded_by_user_id"] == "DOC-CARDIO-1"
    assert data["notes"] == "Checkup successful, vitals normal"

    # Consultation duration computed (~900 seconds / 15 minutes)
    assert 890 <= data["consultation_duration_seconds"] <= 920
    assert 14.8 <= data["consultation_duration_minutes"] <= 15.2

    # Doctor availability reset
    assert data["doctor_availability"] == "AVAILABLE"

    # Timestamp records logged immutably
    history = timestamp_store.get_by_token(token.token_id)
    stages = [h.stage for h in history]
    assert JourneyStage.CONSULTATION_END in stages
    assert JourneyStage.COMPLETED in stages


# =========================================================================
# 2. ACCEPTANCE CRITERIA: REJECT COMPLETION ON NON-CONSULTATION STATUSES
# =========================================================================

def test_reject_completion_on_waiting_status():
    """Verify rejection if patient is WAITING (has not been called/started)."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-REJ-WAIT",
        patient_id="PAT-502",
        patient_name="Pam Beesly",
        doctor_id="DOC-1",
        doctor_name="Dr. Doctor",
        department_id="DEP-GEN",
        department_name="General Medicine",
    )
    assert token.status == QueueStatus.WAITING

    response = client.patch(
        f"/api/queue/{token.token_id}/complete",
        json={"recorded_by_user_id": "DOC-1"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "In Consultation" in str(body["error"])


def test_reject_completion_on_called_status():
    """Verify rejection if patient is CALLED (has not entered consultation yet)."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-REJ-CALL",
        patient_id="PAT-503",
        patient_name="Michael Scott",
        doctor_id="DOC-1",
        doctor_name="Dr. Doctor",
        department_id="DEP-GEN",
        department_name="General Medicine",
    )
    token.status = QueueStatus.CALLED

    response = client.patch(
        f"/api/queue/{token.token_id}/complete",
        json={"recorded_by_user_id": "DOC-1"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "In Consultation" in str(body["error"])


def test_reject_completion_on_already_completed_status():
    """Verify rejection if patient is already COMPLETED."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-REJ-CMP",
        patient_id="PAT-504",
        patient_name="Dwight Schrute",
        doctor_id="DOC-1",
        doctor_name="Dr. Doctor",
        department_id="DEP-GEN",
        department_name="General Medicine",
    )
    token.status = QueueStatus.COMPLETED

    response = client.patch(
        f"/api/queue/{token.token_id}/complete",
        json={"recorded_by_user_id": "DOC-1"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False


def test_reject_completion_on_no_show_or_abandoned_status():
    """Verify rejection if patient was marked NO_SHOW or ABANDONED."""
    t_noshow = queue_service_instance.add_to_queue(
        appointment_id="APT-REJ-NS",
        patient_id="PAT-505",
        patient_name="Stanley Hudson",
        doctor_id="DOC-1",
        doctor_name="Dr. Doctor",
        department_id="DEP-GEN",
        department_name="General Medicine",
    )
    t_noshow.status = QueueStatus.NO_SHOW

    res_ns = client.patch(
        f"/api/queue/{t_noshow.token_id}/complete",
        json={"recorded_by_user_id": "DOC-1"},
    )
    assert res_ns.status_code == 422

    t_aband = queue_service_instance.add_to_queue(
        appointment_id="APT-REJ-AB",
        patient_id="PAT-506",
        patient_name="Phyllis Vance",
        doctor_id="DOC-1",
        doctor_name="Dr. Doctor",
        department_id="DEP-GEN",
        department_name="General Medicine",
    )
    t_aband.status = QueueStatus.ABANDONED

    res_ab = client.patch(
        f"/api/queue/{t_aband.token_id}/complete",
        json={"recorded_by_user_id": "DOC-1"},
    )
    assert res_ab.status_code == 422


# =========================================================================
# 3. ACCEPTANCE CRITERIA: REMOVED FROM ACTIVE LIVE QUEUE
# =========================================================================

def test_completed_patient_removed_from_live_queue():
    """Verify completed patient drops from live queue, allowing doctor to take next call."""
    t1 = queue_service_instance.add_to_queue(
        appointment_id="APT-LIVE-1",
        patient_id="PAT-601",
        patient_name="Patient Active",
        doctor_id="DOC-1",
        doctor_name="Dr. Doctor",
        department_id="DEP-GEN",
        department_name="General Medicine",
    )
    t2 = queue_service_instance.add_to_queue(
        appointment_id="APT-LIVE-2",
        patient_id="PAT-602",
        patient_name="Patient Next In Line",
        doctor_id="DOC-1",
        doctor_name="Dr. Doctor",
        department_id="DEP-GEN",
        department_name="General Medicine",
    )
    t1.status = QueueStatus.IN_CONSULTATION

    # Live queue currently contains both t1 and t2
    res_before = client.get("/api/queue/live")
    ids_before = [t["token_id"] for t in res_before.json()["data"]]
    assert t1.token_id in ids_before
    assert t2.token_id in ids_before

    # Complete t1
    client.patch(
        f"/api/queue/{t1.token_id}/complete",
        json={"recorded_by_user_id": "DOC-1"},
    )

    # Live queue now contains only t2
    res_after = client.get("/api/queue/live")
    ids_after = [t["token_id"] for t in res_after.json()["data"]]
    assert t1.token_id not in ids_after
    assert t2.token_id in ids_after


# =========================================================================
# 4. ACCEPTANCE CRITERIA: VISIT HISTORY ARCHIVE
# =========================================================================

def test_visit_history_archive_created_and_queryable():
    """Verify completed consultation is archived to visit history and queryable by patient."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-ARCHIVE-1",
        patient_id="PAT-ARCHIVE-701",
        patient_name="Andy Bernard",
        doctor_id="DOC-ENT",
        doctor_name="Dr. Ear",
        department_id="DEP-ENT",
        department_name="Otolaryngology",
    )
    token.status = QueueStatus.IN_CONSULTATION
    token.consultation_start_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    patch_res = client.patch(
        f"/api/queue/{token.token_id}/complete",
        json={"recorded_by_user_id": "DOC-ENT", "notes": "Ear canal clear"},
    )
    assert patch_res.status_code == 200

    # Query patient visit history endpoint
    visits_res = client.get(f"/api/queue/patients/PAT-ARCHIVE-701/visits")
    assert visits_res.status_code == 200
    visits_data = visits_res.json()["data"]
    assert visits_data["patient_id"] == "PAT-ARCHIVE-701"
    assert visits_data["total_visits"] == 1
    assert visits_data["visits"][0]["doctor_id"] == "DOC-ENT"
    assert visits_data["visits"][0]["notes"] == "Ear canal clear"
    assert visits_data["visits"][0]["duration_minutes"] >= 9.8


# =========================================================================
# 5. ACCEPTANCE CRITERIA: DOCTOR WORKLOAD & AVAILABILITY
# =========================================================================

def test_doctor_availability_and_workload_lifecycle():
    """Verify doctor availability resets to AVAILABLE and workload counter increments."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-DOC-1",
        patient_id="PAT-801",
        patient_name="Oscar Martinez",
        doctor_id="DOC-BUSY-1",
        doctor_name="Dr. Busy",
        department_id="DEP-GEN",
        department_name="General Medicine",
    )
    token.status = QueueStatus.IN_CONSULTATION
    token.consultation_start_time = datetime.now(timezone.utc) - timedelta(minutes=20)
    doctor_workload_store.set_busy("DOC-BUSY-1", "Dr. Busy", token.token_id)

    # Doctor is currently BUSY
    doc_state = doctor_workload_store.get_doctor_workload("DOC-BUSY-1")
    assert doc_state.availability == DoctorAvailability.BUSY

    # Complete consultation
    res = client.patch(
        f"/api/queue/{token.token_id}/complete",
        json={"recorded_by_user_id": "DOC-BUSY-1"},
    )
    assert res.status_code == 200

    # Query doctor workload endpoint
    workload_res = client.get("/api/queue/doctors/DOC-BUSY-1/workload")
    assert workload_res.status_code == 200
    workload_data = workload_res.json()["data"]
    assert workload_data["doctor_id"] == "DOC-BUSY-1"
    assert workload_data["availability"] == "AVAILABLE"
    assert workload_data["completed_consultations_count"] == 1
    assert workload_data["total_consultation_seconds"] >= 1190


# =========================================================================
# 6. ACCEPTANCE CRITERIA: OPERATIONAL REPORTING ANALYTICS
# =========================================================================

def test_completed_consultation_analytics():
    """Verify aggregated metrics: total completed, average duration, doctor/department breakdowns."""
    # Complete 2 consultations in Cardiology
    for i in range(2):
        t = queue_service_instance.add_to_queue(
            appointment_id=f"APT-AN-CARD-{i}",
            patient_id=f"PAT-C-{i}",
            patient_name=f"Patient C{i}",
            doctor_id="DOC-CARDIO",
            doctor_name="Dr. Heart",
            department_id="DEP-CARDIO",
            department_name="Cardiology",
        )
        t.status = QueueStatus.IN_CONSULTATION
        t.consultation_start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        client.patch(f"/api/queue/{t.token_id}/complete", json={"recorded_by_user_id": "DOC-CARDIO"})

    # Complete 1 consultation in Orthopedics
    t_ortho = queue_service_instance.add_to_queue(
        appointment_id="APT-AN-ORTHO-1",
        patient_id="PAT-O-1",
        patient_name="Patient O1",
        doctor_id="DOC-ORTHO",
        doctor_name="Dr. Bone",
        department_id="DEP-ORTHO",
        department_name="Orthopedics",
    )
    t_ortho.status = QueueStatus.IN_CONSULTATION
    t_ortho.consultation_start_time = datetime.now(timezone.utc) - timedelta(minutes=20)
    client.patch(f"/api/queue/{t_ortho.token_id}/complete", json={"recorded_by_user_id": "DOC-ORTHO"})

    res = client.get("/api/queue/analytics/completed")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["total_completed"] == 3
    assert data["by_department"]["DEP-CARDIO"] == 2
    assert data["by_department"]["DEP-ORTHO"] == 1
    assert data["by_doctor"]["DOC-CARDIO"] == 2
    assert data["by_doctor"]["DOC-ORTHO"] == 1
    assert data["average_duration_minutes"] >= 10.0
