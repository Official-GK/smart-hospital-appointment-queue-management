import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.queue.models.doctor_workload_models import (
    DoctorAvailability,
    doctor_workload_store,
)
from backend.services.queue.models.visit_history_models import visit_history_store
from backend.services.queue.models.timestamp_models import timestamp_store
from backend.services.queue.schemas.queue_schemas import QueueStatus
from backend.services.queue.services.queue_service import queue_service_instance

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_all_stores():
    """Reset in-memory state before and after each test."""
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
# 1. ACCEPTANCE CRITERIA: SPECIALTY MATCHING VIA DEPARTMENT ID
# =========================================================================

def test_ranking_returns_only_matching_department_doctors():
    """Verify allocation suggestion filters doctors strictly by department specialty."""
    # Register 2 doctors in Cardiology and 1 in Orthopedics
    doctor_workload_store.register_doctor("DOC-C1", "Dr. Heart One", "DEP-CARDIO", DoctorAvailability.AVAILABLE)
    doctor_workload_store.register_doctor("DOC-C2", "Dr. Heart Two", "DEP-CARDIO", DoctorAvailability.AVAILABLE)
    doctor_workload_store.register_doctor("DOC-O1", "Dr. Bone", "DEP-ORTHO", DoctorAvailability.AVAILABLE)

    res = client.get("/api/queue/allocation/suggest?department_id=DEP-CARDIO")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]

    assert data["department_id"] == "DEP-CARDIO"
    assert data["total_eligible_doctors"] == 2
    doc_ids = [d["doctor_id"] for d in data["suggestions"]]
    assert "DOC-C1" in doc_ids
    assert "DOC-C2" in doc_ids
    assert "DOC-O1" not in doc_ids


# =========================================================================
# 2. ACCEPTANCE CRITERIA: EXCLUSION OF ABSENT OR OFF-DUTY DOCTORS
# =========================================================================

def test_doctors_marked_absent_or_off_duty_are_excluded():
    """Verify doctors marked Absent or Off-Duty are excluded from receiving new allocations."""
    doctor_workload_store.register_doctor("DOC-ON", "Dr. On Duty", "DEP-GEN", DoctorAvailability.AVAILABLE)
    doctor_workload_store.register_doctor("DOC-OFF", "Dr. Off Duty", "DEP-GEN", DoctorAvailability.OFF_DUTY)
    doctor_workload_store.register_doctor("DOC-ABS", "Dr. Absent", "DEP-GEN", DoctorAvailability.ABSENT)

    res = client.get("/api/queue/allocation/suggest?department_id=DEP-GEN")
    assert res.status_code == 200
    suggestions = res.json()["data"]["suggestions"]

    doc_ids = [s["doctor_id"] for s in suggestions]
    assert "DOC-ON" in doc_ids
    assert "DOC-OFF" not in doc_ids
    assert "DOC-ABS" not in doc_ids



# =========================================================================
# 3. ACCEPTANCE CRITERIA: RANKING BY LIGHTEST ACTIVE QUEUE LOAD
# =========================================================================

def test_ranking_sorted_by_ascending_queue_length():
    """Verify allocation logic ranks doctors by ascending queue length (lightest load first)."""
    doctor_workload_store.register_doctor("DOC-BUSY", "Dr. Heavy Load", "DEP-CARDIO", DoctorAvailability.AVAILABLE)
    doctor_workload_store.register_doctor("DOC-FREE", "Dr. Light Load", "DEP-CARDIO", DoctorAvailability.AVAILABLE)

    # Give DOC-BUSY 2 waiting patients
    t1 = queue_service_instance.add_to_queue(
        appointment_id="APT-B1", patient_id="P1", patient_name="P1",
        doctor_id="DOC-BUSY", doctor_name="Dr. Heavy Load", department_id="DEP-CARDIO", department_name="Cardiology",
    )
    t2 = queue_service_instance.add_to_queue(
        appointment_id="APT-B2", patient_id="P2", patient_name="P2",
        doctor_id="DOC-BUSY", doctor_name="Dr. Heavy Load", department_id="DEP-CARDIO", department_name="Cardiology",
    )

    # DOC-FREE has 0 waiting patients
    res = client.get("/api/queue/allocation/suggest?department_id=DEP-CARDIO")
    assert res.status_code == 200
    suggestions = res.json()["data"]["suggestions"]

    assert len(suggestions) == 2
    # Rank #1 must be DOC-FREE (0 patients ahead)
    assert suggestions[0]["doctor_id"] == "DOC-FREE"
    assert suggestions[0]["active_queue_length"] == 0
    assert suggestions[0]["is_recommended"] is True

    # Rank #2 must be DOC-BUSY (2 patients ahead)
    assert suggestions[1]["doctor_id"] == "DOC-BUSY"
    assert suggestions[1]["active_queue_length"] == 2
    assert suggestions[1]["is_recommended"] is False


# =========================================================================
# 4. ACCEPTANCE CRITERIA: MANUAL STAFF ASSIGNMENT AND OVERRIDE
# =========================================================================

def test_manual_assignment_succeeds_for_available_doctor():
    """Verify staff can confirm doctor assignment from the ranked list."""
    doctor_workload_store.register_doctor("DOC-TARGET", "Dr. Target", "DEP-GEN", DoctorAvailability.AVAILABLE)

    token = queue_service_instance.add_to_queue(
        appointment_id="APT-ASGN-1", patient_id="P-ASGN", patient_name="Patient Assign",
        doctor_id="DOC-ORIG", doctor_name="Dr. Original", department_id="DEP-GEN", department_name="General Medicine",
    )

    patch_res = client.patch(
        f"/api/queue/{token.token_id}/assign-doctor",
        json={"doctor_id": "DOC-TARGET", "recorded_by_user_id": "STAFF-DESK-1", "notes": "Assigned via ranking"},
    )
    assert patch_res.status_code == 200
    body = patch_res.json()
    assert body["success"] is True
    assert body["data"]["doctor_id"] == "DOC-TARGET"
    assert body["data"]["doctor_name"] == "Dr. Target"


def test_manual_assignment_rejected_for_unavailable_doctor():
    """Verify attempt to manually assign an Absent or Off-Duty doctor is rejected with 422."""
    doctor_workload_store.register_doctor("DOC-UNAVAIL", "Dr. Sick Leave", "DEP-GEN", DoctorAvailability.ABSENT)

    token = queue_service_instance.add_to_queue(
        appointment_id="APT-ASGN-2", patient_id="P-ASGN2", patient_name="Patient",
        doctor_id="DOC-ORIG", doctor_name="Dr. Original", department_id="DEP-GEN", department_name="General Medicine",
    )

    patch_res = client.patch(
        f"/api/queue/{token.token_id}/assign-doctor",
        json={"doctor_id": "DOC-UNAVAIL", "recorded_by_user_id": "STAFF-DESK-1"},
    )
    assert patch_res.status_code == 422
    body = patch_res.json()
    assert body["success"] is False
    assert "Absent or Off-Duty" in str(body["error"])


# =========================================================================
# 5. ACCEPTANCE CRITERIA: REASSIGNMENT DYNAMICALLY RECALCULATES WAIT TIMES
# =========================================================================

def test_reassignment_updates_wait_times_for_both_doctors():
    """Verify moving a patient recalculates queue wait times for both old and new doctor queues."""
    # Doctor 1 has 2 patients: T1 and T2
    t1 = queue_service_instance.add_to_queue(
        appointment_id="APT-MV-1", patient_id="P1", patient_name="P1",
        doctor_id="DOC-D1", doctor_name="Dr. One", department_id="DEP-GEN", department_name="Clinic",
    )
    t2 = queue_service_instance.add_to_queue(
        appointment_id="APT-MV-2", patient_id="P2", patient_name="P2",
        doctor_id="DOC-D1", doctor_name="Dr. One", department_id="DEP-GEN", department_name="Clinic",
    )
    # T2 initially has 1 patient ahead (T1) -> 10 mins
    assert t2.estimated_wait_minutes == 10

    # Doctor 2 is available and currently has 0 patients
    doctor_workload_store.register_doctor("DOC-D2", "Dr. Two", "DEP-GEN", DoctorAvailability.AVAILABLE)

    # Reassign T1 from Doctor 1 to Doctor 2
    client.patch(
        f"/api/queue/{t1.token_id}/assign-doctor",
        json={"doctor_id": "DOC-D2", "recorded_by_user_id": "STAFF-01", "notes": "Rebalancing load"},
    )

    # After reassignment:
    # T2 is now first in Doctor 1's queue (0 ahead) -> 0 mins
    assert t2.estimated_wait_minutes == 0
    # T1 is now in Doctor 2's queue (0 ahead) -> 0 mins
    assert t1.doctor_id == "DOC-D2"
