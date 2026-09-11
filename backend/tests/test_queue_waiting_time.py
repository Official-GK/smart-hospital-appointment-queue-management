from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.queue.models.timestamp_models import timestamp_store
from backend.services.queue.models.doctor_workload_models import doctor_workload_store
from backend.services.queue.models.visit_history_models import VisitRecord, visit_history_store
from backend.services.queue.schemas.queue_schemas import QueuePriority, QueueStatus
from backend.services.queue.services.queue_service import queue_service_instance

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_all_stores():
    """Reset all state before and after each test."""
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
# 1. ACCEPTANCE CRITERIA: CALCULATION USING REAL DOCTOR AVERAGE (TIER 1)
# =========================================================================

def test_wait_time_with_real_doctor_average():
    """Verify calculation uses real doctor average from VisitHistoryStore instead of placeholder."""
    # Seed 2 completed visits of 15.0 minutes for Dr. Strange
    v1 = VisitRecord.create(
        token_id="TOK-HIST-1", appointment_id="APT-H1", patient_id="P-H1", patient_name="P1",
        doctor_id="DOC-STRANGE", doctor_name="Dr. Strange", department_id="DEP-MAGIC", department_name="Mystic",
        consultation_start_time=datetime.now(timezone.utc) - timedelta(minutes=15),
        consultation_end_time=datetime.now(timezone.utc),
        duration_seconds=900.0, recorded_by_user_id="DOC-STRANGE",
    )
    v2 = VisitRecord.create(
        token_id="TOK-HIST-2", appointment_id="APT-H2", patient_id="P-H2", patient_name="P2",
        doctor_id="DOC-STRANGE", doctor_name="Dr. Strange", department_id="DEP-MAGIC", department_name="Mystic",
        consultation_start_time=datetime.now(timezone.utc) - timedelta(minutes=15),
        consultation_end_time=datetime.now(timezone.utc),
        duration_seconds=900.0, recorded_by_user_id="DOC-STRANGE",
    )
    visit_history_store.append(v1)
    visit_history_store.append(v2)

    # Queue 2 patients: T1 and T2
    t1 = queue_service_instance.add_to_queue(
        appointment_id="APT-WT-1", patient_id="PAT-1", patient_name="Patient One",
        doctor_id="DOC-STRANGE", doctor_name="Dr. Strange", department_id="DEP-MAGIC", department_name="Mystic",
    )
    t2 = queue_service_instance.add_to_queue(
        appointment_id="APT-WT-2", patient_id="PAT-2", patient_name="Patient Two",
        doctor_id="DOC-STRANGE", doctor_name="Dr. Strange", department_id="DEP-MAGIC", department_name="Mystic",
    )

    # Fetch wait time for Patient Two (has 1 patient ahead: T1)
    res = client.get(f"/api/queue/{t2.token_id}/wait-time")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]

    assert data["token_id"] == t2.token_id
    assert data["patients_ahead"] == 1
    assert data["average_consultation_minutes"] == 15.0
    assert data["estimated_wait_minutes"] == 15
    assert data["calculation_source"] == "doctor_average"


# =========================================================================
# 2. ACCEPTANCE CRITERIA: FALLBACK CHAIN (TIER 2 & TIER 3)
# =========================================================================

def test_fallback_to_department_average():
    """Verify fallback to department average when the assigned doctor has no completed visits."""
    # Seed department visit for Cardiology (Dr. Heart completed 20.0 min visit)
    v_dept = VisitRecord.create(
        token_id="TOK-HIST-3", appointment_id="APT-H3", patient_id="P-H3", patient_name="P3",
        doctor_id="DOC-HEART", doctor_name="Dr. Heart", department_id="DEP-CARDIO", department_name="Cardiology",
        consultation_start_time=datetime.now(timezone.utc) - timedelta(minutes=20),
        consultation_end_time=datetime.now(timezone.utc),
        duration_seconds=1200.0, recorded_by_user_id="DOC-HEART",
    )
    visit_history_store.append(v_dept)

    # New doctor (Dr. Junior) has zero visits, but is in Cardiology
    t1 = queue_service_instance.add_to_queue(
        appointment_id="APT-DEPT-1", patient_id="P-D1", patient_name="First Patient",
        doctor_id="DOC-JUNIOR", doctor_name="Dr. Junior", department_id="DEP-CARDIO", department_name="Cardiology",
    )
    t2 = queue_service_instance.add_to_queue(
        appointment_id="APT-DEPT-2", patient_id="P-D2", patient_name="Second Patient",
        doctor_id="DOC-JUNIOR", doctor_name="Dr. Junior", department_id="DEP-CARDIO", department_name="Cardiology",
    )

    res = client.get(f"/api/queue/{t2.token_id}/wait-time")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["patients_ahead"] == 1
    assert data["average_consultation_minutes"] == 20.0
    assert data["estimated_wait_minutes"] == 20
    assert data["calculation_source"] == "department_average"


def test_fallback_to_default_benchmark():
    """Verify fallback to default benchmark (10.0 mins) when neither doctor nor department has visits."""
    t1 = queue_service_instance.add_to_queue(
        appointment_id="APT-DEF-1", patient_id="P-DF1", patient_name="P1",
        doctor_id="DOC-NEW", doctor_name="Dr. New", department_id="DEP-NEW", department_name="New Clinic",
    )
    t2 = queue_service_instance.add_to_queue(
        appointment_id="APT-DEF-2", patient_id="P-DF2", patient_name="P2",
        doctor_id="DOC-NEW", doctor_name="Dr. New", department_id="DEP-NEW", department_name="New Clinic",
    )

    res = client.get(f"/api/queue/{t2.token_id}/wait-time")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["patients_ahead"] == 1
    assert data["average_consultation_minutes"] == 10.0
    assert data["estimated_wait_minutes"] == 10
    assert data["calculation_source"] == "default_benchmark"


# =========================================================================
# 3. ACCEPTANCE CRITERIA: DYNAMIC RECALCULATION ON QUEUE PROGRESSION
# =========================================================================

def test_wait_time_recalculation_on_consultation_completion():
    """Verify remaining waiting patient's wait time drops when patient ahead completes consultation."""
    t1 = queue_service_instance.add_to_queue(
        appointment_id="APT-DYN-1", patient_id="P-DN1", patient_name="P1",
        doctor_id="DOC-1", doctor_name="Dr. Doctor", department_id="DEP-1", department_name="Clinic",
    )
    t2 = queue_service_instance.add_to_queue(
        appointment_id="APT-DYN-2", patient_id="P-DN2", patient_name="P2",
        doctor_id="DOC-1", doctor_name="Dr. Doctor", department_id="DEP-1", department_name="Clinic",
    )
    t1.status = QueueStatus.IN_CONSULTATION

    # Before completion: T2 has 1 ahead (T1 in consultation)
    res_before = client.get(f"/api/queue/{t2.token_id}/wait-time").json()["data"]
    assert res_before["patients_ahead"] == 1
    assert res_before["estimated_wait_minutes"] == 10

    # T1 completes consultation
    client.patch(f"/api/queue/{t1.token_id}/complete", json={"recorded_by_user_id": "DOC-1"})

    # After completion: T2 has 0 ahead
    res_after = client.get(f"/api/queue/{t2.token_id}/wait-time").json()["data"]
    assert res_after["patients_ahead"] == 0
    assert res_after["estimated_wait_minutes"] == 0


def test_wait_time_recalculation_on_abandonment_replaces_old_placeholder():
    """Verify that abandonment dynamically recalculates wait times without the old placeholder."""
    t1 = queue_service_instance.add_to_queue(
        appointment_id="APT-AB-1", patient_id="P-AB1", patient_name="P1",
        doctor_id="DOC-CARDIO", doctor_name="Dr. Smith", department_id="DEP-CARDIO", department_name="Cardiology",
    )
    t2 = queue_service_instance.add_to_queue(
        appointment_id="APT-AB-2", patient_id="P-AB2", patient_name="P2",
        doctor_id="DOC-CARDIO", doctor_name="Dr. Smith", department_id="DEP-CARDIO", department_name="Cardiology",
    )
    t3 = queue_service_instance.add_to_queue(
        appointment_id="APT-AB-3", patient_id="P-AB3", patient_name="P3",
        doctor_id="DOC-CARDIO", doctor_name="Dr. Smith", department_id="DEP-CARDIO", department_name="Cardiology",
    )

    # Initial: T3 has 2 patients ahead -> 2 * 10 = 20 mins
    res_init = client.get(f"/api/queue/{t3.token_id}/wait-time").json()["data"]
    assert res_init["patients_ahead"] == 2
    assert res_init["estimated_wait_minutes"] == 20

    # T1 abandons
    client.patch(f"/api/queue/{t1.token_id}/abandon", json={"reason": "Left queue"})

    # T3 now has 1 patient ahead (T2) -> 1 * 10 = 10 mins
    res_after = client.get(f"/api/queue/{t3.token_id}/wait-time").json()["data"]
    assert res_after["patients_ahead"] == 1
    assert res_after["estimated_wait_minutes"] == 10


def test_wait_time_recalculation_on_no_show():
    """Verify wait time drops when patient ahead is flagged as No-Show."""
    t1 = queue_service_instance.add_to_queue(
        appointment_id="APT-NS-W1", patient_id="P-NS1", patient_name="P1",
        doctor_id="DOC-1", doctor_name="Dr. Doctor", department_id="DEP-1", department_name="Clinic",
    )
    t2 = queue_service_instance.add_to_queue(
        appointment_id="APT-NS-W2", patient_id="P-NS2", patient_name="P2",
        doctor_id="DOC-1", doctor_name="Dr. Doctor", department_id="DEP-1", department_name="Clinic",
    )
    t1.status = QueueStatus.CALLED

    # T1 is called, mark as No-Show
    client.patch(f"/api/queue/{t1.token_id}/no-show", json={"recorded_by_user_id": "STF-1"})

    # T2 is now first in line
    res = client.get(f"/api/queue/{t2.token_id}/wait-time").json()["data"]
    assert res["patients_ahead"] == 0
    assert res["estimated_wait_minutes"] == 0


def test_priority_override_adjusts_wait_time():
    """Verify an Emergency patient arriving ahead increases subsequent patients' wait times."""
    t_normal = queue_service_instance.add_to_queue(
        appointment_id="APT-NORM-1", patient_id="P-NORM", patient_name="Normal Patient",
        doctor_id="DOC-ER", doctor_name="Dr. ER", department_id="DEP-ER", department_name="Emergency",
        priority=QueuePriority.NORMAL,
    )
    # T_normal is currently first in line (0 ahead)
    assert client.get(f"/api/queue/{t_normal.token_id}/wait-time").json()["data"]["patients_ahead"] == 0

    # Emergency patient arrives later in time
    t_emergency = queue_service_instance.add_to_queue(
        appointment_id="APT-EMERG-1", patient_id="P-EMERG", patient_name="Emergency Patient",
        doctor_id="DOC-ER", doctor_name="Dr. ER", department_id="DEP-ER", department_name="Emergency",
        priority=QueuePriority.EMERGENCY,
    )

    # T_emergency is placed at the front of the queue ahead of T_normal
    res_normal = client.get(f"/api/queue/{t_normal.token_id}/wait-time").json()["data"]
    assert res_normal["patients_ahead"] == 1
    assert res_normal["estimated_wait_minutes"] == 10
