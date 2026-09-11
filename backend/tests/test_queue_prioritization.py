import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.queue.models.timestamp_models import (
    JourneyStage,
    timestamp_store,
)
from backend.services.queue.schemas.queue_schemas import QueuePriority, QueueStatus
from backend.services.queue.services.queue_service import queue_service_instance
from backend.services.queue.services.waiting_time_service import waiting_time_service_instance

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_all_stores():
    """Reset in-memory state before and after each test."""
    queue_service_instance._tokens.clear()
    queue_service_instance._token_counter = 100
    timestamp_store.clear()
    yield
    queue_service_instance._tokens.clear()
    timestamp_store.clear()


# =========================================================================
# 1. ACCEPTANCE CRITERIA: 5 PRIORITY CATEGORIES & NATURAL ORDERING
# =========================================================================

def test_priority_categories_natural_ordering():
    """
    Verify tokens ordered by priority:
    EMERGENCY > SENIOR_CITIZEN > VIP > SCHEDULED > WALK_IN
    """
    # Create tokens in inverse order
    t_walkin = queue_service_instance.add_to_queue(
        appointment_id="APT-W", patient_id="P-W", patient_name="Walk-in Patient",
        doctor_id="DOC-PRIO", doctor_name="Dr. Triage", department_id="DEP-GEN", department_name="General",
        priority=QueuePriority.WALK_IN,
    )
    t_sched = queue_service_instance.add_to_queue(
        appointment_id="APT-S", patient_id="P-S", patient_name="Scheduled Patient",
        doctor_id="DOC-PRIO", doctor_name="Dr. Triage", department_id="DEP-GEN", department_name="General",
        priority=QueuePriority.SCHEDULED,
    )
    t_vip = queue_service_instance.add_to_queue(
        appointment_id="APT-V", patient_id="P-V", patient_name="VIP Patient",
        doctor_id="DOC-PRIO", doctor_name="Dr. Triage", department_id="DEP-GEN", department_name="General",
        priority=QueuePriority.VIP,
    )
    t_senior = queue_service_instance.add_to_queue(
        appointment_id="APT-SR", patient_id="P-SR", patient_name="Senior Citizen Patient",
        doctor_id="DOC-PRIO", doctor_name="Dr. Triage", department_id="DEP-GEN", department_name="General",
        priority=QueuePriority.SENIOR_CITIZEN,
    )
    t_emg = queue_service_instance.add_to_queue(
        appointment_id="APT-E", patient_id="P-E", patient_name="Emergency Patient",
        doctor_id="DOC-PRIO", doctor_name="Dr. Triage", department_id="DEP-GEN", department_name="General",
        priority=QueuePriority.EMERGENCY,
    )

    ordered = waiting_time_service_instance.get_ordered_active_queue(doctor_id="DOC-PRIO")
    ordered_ids = [t.token_id for t in ordered]

    # Must be ordered strictly by priority rank despite arrival sequence
    expected_order = [t_emg.token_id, t_senior.token_id, t_vip.token_id, t_sched.token_id, t_walkin.token_id]
    assert ordered_ids == expected_order


# =========================================================================
# 2. ACCEPTANCE CRITERIA: MANUAL ELEVATION WITH BADGE METADATA
# =========================================================================

def test_manual_priority_elevation_success():
    """Verify staff can manually elevate a token with a reason and badge fields populate."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-ELEV-1", patient_id="P-101", patient_name="John Doe",
        doctor_id="DOC-1", doctor_name="Dr. Smith", department_id="DEP-1", department_name="General",
        priority=QueuePriority.WALK_IN,
    )
    assert token.is_manually_elevated is False
    assert token.elevation_reason is None

    payload = {
        "priority": "Emergency",
        "reason": "Severe chest pain and difficulty breathing reported at counter",
        "recorded_by_user_id": "STAFF-TRIAGE-01",
    }

    res = client.patch(f"/api/queue/{token.token_id}/priority", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True

    data = body["data"]
    assert data["previous_priority"] == "Walk-in"
    assert data["new_priority"] == "Emergency"
    assert data["reason"] == "Severe chest pain and difficulty breathing reported at counter"
    assert data["recorded_by_user_id"] == "STAFF-TRIAGE-01"

    token_data = data["token"]
    assert token_data["priority"] == "Emergency"
    assert token_data["is_manually_elevated"] is True
    assert token_data["elevation_reason"] == "Severe chest pain and difficulty breathing reported at counter"


# =========================================================================
# 3. ACCEPTANCE CRITERIA: REJECTED ELEVATION ON MISSING/EMPTY REASON (422)
# =========================================================================

def test_manual_priority_elevation_rejected_empty_reason():
    """Verify elevation request is rejected with 422 if reason is empty or whitespace."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-ELEV-2", patient_id="P-102", patient_name="Jane Doe",
        doctor_id="DOC-1", doctor_name="Dr. Smith", department_id="DEP-1", department_name="General",
        priority=QueuePriority.WALK_IN,
    )

    # Empty string reason
    res_empty = client.patch(
        f"/api/queue/{token.token_id}/priority",
        json={"priority": "VIP", "reason": "", "recorded_by_user_id": "STAFF-01"},
    )
    assert res_empty.status_code == 422

    # Whitespace only reason
    res_ws = client.patch(
        f"/api/queue/{token.token_id}/priority",
        json={"priority": "VIP", "reason": "   ", "recorded_by_user_id": "STAFF-01"},
    )
    assert res_ws.status_code == 422


def test_manual_priority_elevation_not_found():
    """Verify elevation returns 404 for unknown token."""
    res = client.patch(
        "/api/queue/UNKNOWN-TOKEN/priority",
        json={"priority": "VIP", "reason": "VIP patient arrived", "recorded_by_user_id": "STAFF-01"},
    )
    assert res.status_code == 404


# =========================================================================
# 4. ACCEPTANCE CRITERIA: REORDERING PROOF (ELEVATED TOKEN JUMPS AHEAD)
# =========================================================================

def test_elevation_reorders_queue_and_recalculates_wait_time():
    """
    Verify that manually elevating a patient moves them ahead of lower-priority patients
    who arrived earlier, and dynamically recalculates wait times.
    """
    # Patient 1: Scheduled (Normal) arriving first
    t1 = queue_service_instance.add_to_queue(
        appointment_id="APT-REORDER-1", patient_id="P-01", patient_name="Normal Patient 1",
        doctor_id="DOC-REORDER", doctor_name="Dr. Quick", department_id="DEP-1", department_name="General",
        priority=QueuePriority.SCHEDULED,
    )

    # Patient 2: Walk-in arriving second
    t2 = queue_service_instance.add_to_queue(
        appointment_id="APT-REORDER-2", patient_id="P-02", patient_name="Walk-in Patient 2",
        doctor_id="DOC-REORDER", doctor_name="Dr. Quick", department_id="DEP-1", department_name="General",
        priority=QueuePriority.WALK_IN,
    )

    # Initially: T1 is first (0 wait), T2 is second (10 mins wait)
    queue_initial = waiting_time_service_instance.get_ordered_active_queue(doctor_id="DOC-REORDER")
    assert [t.token_id for t in queue_initial] == [t1.token_id, t2.token_id]
    assert t1.estimated_wait_minutes == 0
    assert t2.estimated_wait_minutes == 10

    # Elevate Patient 2 (Walk-in) to EMERGENCY
    patch_res = client.patch(
        f"/api/queue/{t2.token_id}/priority",
        json={
            "priority": "Emergency",
            "reason": "Sudden acute allergic reaction in waiting hall",
            "recorded_by_user_id": "STAFF-NURSE-01",
        },
    )
    assert patch_res.status_code == 200

    # REORDERING PROOF:
    # Queue order should now be: [T2 (Emergency), T1 (Scheduled)]
    queue_after = waiting_time_service_instance.get_ordered_active_queue(doctor_id="DOC-REORDER")
    assert [t.token_id for t in queue_after] == [t2.token_id, t1.token_id]

    # Wait-time verification:
    # T2 now has 0 ahead -> 0 mins wait
    # T1 now pushed behind T2 -> 10 mins wait
    t1_updated = queue_service_instance.get_token(t1.token_id)
    t2_updated = queue_service_instance.get_token(t2.token_id)
    assert t2_updated.estimated_wait_minutes == 0
    assert t1_updated.estimated_wait_minutes == 10


# =========================================================================
# 5. ACCEPTANCE CRITERIA: IMMUTABLE AUDIT LOGGING IN TIMESTAMP STORE
# =========================================================================

def test_elevation_creates_audit_record_in_timestamp_store():
    """Verify manual elevation generates an OperationalTimestampRecord with stage PRIORITY_ELEVATED."""
    token = queue_service_instance.add_to_queue(
        appointment_id="APT-AUDIT-1", patient_id="P-AUDIT", patient_name="Audit Patient",
        doctor_id="DOC-1", doctor_name="Dr. Smith", department_id="DEP-1", department_name="General",
        priority=QueuePriority.WALK_IN,
    )

    client.patch(
        f"/api/queue/{token.token_id}/priority",
        json={
            "priority": "Senior Citizen",
            "reason": "Age verified as 78 at front desk registration",
            "recorded_by_user_id": "RECEPTION-01",
        },
    )

    audit_records = [
        r for r in timestamp_store.get_by_token(token.token_id)
        if r.stage == JourneyStage.PRIORITY_ELEVATED
    ]
    assert len(audit_records) == 1
    record = audit_records[0]
    assert record.recorded_by_user_id == "RECEPTION-01"
    assert record.notes == "Age verified as 78 at front desk registration"
    assert record.metadata["previous_priority"] == "Walk-in"
    assert record.metadata["new_priority"] == "Senior Citizen"
    assert record.metadata["elevation_reason"] == "Age verified as 78 at front desk registration"
