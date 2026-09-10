from datetime import date
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_seed_appointment_cancellation_and_inventory():
    # APT-005 is seeded as Cancelled with reason 'Patient Request'
    response = client.get("/api/appointments/APT-005")
    assert response.status_code == 200
    apt = response.json()["data"]
    assert apt["status"] == "Cancelled"
    assert apt["cancellation_details"] is not None
    assert apt["cancellation_details"]["reason"] == "Patient Request"
    assert apt["cancellation_details"]["cancelled_by"] == "STF-001"
    assert apt["timestamps"]["cancelled_at"] is not None

    # Check slot inventory for Dr. Michael Brown (DOC-004)
    slots_res = client.get(f"/api/appointments/inventory/slots?doctor_id=DOC-004&date={date.today().isoformat()}")
    assert slots_res.status_code == 200
    slots = slots_res.json()["data"]
    released_slot = next((s for s in slots if s["slot_time"] == "11:30 AM"), None)
    assert released_slot is not None
    assert released_slot["status"] == "RELEASED"
    assert released_slot["appointment_id"] == "APT-005"


def test_cancel_active_appointment_and_release_slot():
    # 1. Create a new appointment
    today_str = date.today().isoformat()
    create_payload = {
        "patient_id": "PAT-777",
        "patient_name": "Test Cancellation Patient",
        "doctor_id": "DOC-001",
        "department_id": "DEP-CARD",
        "appointment_date": today_str,
        "appointment_time": "03:30 PM",
        "priority": "Normal",
        "notes": "Cardiology consult",
    }
    create_res = client.post("/api/appointments", json=create_payload)
    assert create_res.status_code == 201
    apt = create_res.json()["data"]
    apt_id = apt["appointment_id"]
    assert apt["status"] == "Scheduled"

    # Verify slot is BOOKED initially
    slots_res = client.get(f"/api/appointments/inventory/slots?doctor_id=DOC-001&date={today_str}")
    assert slots_res.status_code == 200
    slot_item = next((s for s in slots_res.json()["data"] if s["slot_time"] == "03:30 PM"), None)
    assert slot_item is not None
    assert slot_item["status"] == "BOOKED"

    # 2. Cancel the appointment with reason and staff_id
    cancel_payload = {
        "reason": "Doctor Unavailable",
        "staff_id": "STF-102",
        "notes": "Doctor called away for emergency surgery",
    }
    cancel_res = client.post(f"/api/appointments/{apt_id}/cancel", json=cancel_payload)
    assert cancel_res.status_code == 200
    cancelled_apt = cancel_res.json()["data"]

    # Verify status, timestamps, and cancellation details
    assert cancelled_apt["status"] == "Cancelled"
    assert cancelled_apt["timestamps"]["cancelled_at"] is not None
    assert cancelled_apt["cancellation_details"]["reason"] == "Doctor Unavailable"
    assert cancelled_apt["cancellation_details"]["cancelled_by"] == "STF-102"
    assert cancelled_apt["cancellation_details"]["notes"] == "Doctor called away for emergency surgery"

    # Verify audit trail
    history = cancelled_apt["history"]
    latest_audit = history[-1]
    assert latest_audit["to_status"] == "Cancelled"
    assert latest_audit["changed_by"] == "STF-102"
    assert "Doctor Unavailable" in latest_audit["notes"]

    # 3. Verify slot inventory is immediately RELEASED
    slots_after = client.get(f"/api/appointments/inventory/slots?doctor_id=DOC-001&date={today_str}")
    assert slots_after.status_code == 200
    released_item = next((s for s in slots_after.json()["data"] if s["slot_time"] == "03:30 PM"), None)
    assert released_item is not None
    assert released_item["status"] == "RELEASED"
    assert released_item["appointment_id"] == apt_id


def test_cancel_checked_in_patient_updates_queue():
    # 1. Create appointment and check in
    create_payload = {
        "patient_id": "PAT-888",
        "patient_name": "Queue Cancellation Patient",
        "doctor_id": "DOC-002",
        "department_id": "DEP-ORTHO",
        "appointment_date": date.today().isoformat(),
        "appointment_time": "04:00 PM",
        "priority": "Normal",
    }
    create_res = client.post("/api/appointments", json=create_payload)
    apt_id = create_res.json()["data"]["appointment_id"]

    check_in_res = client.patch(
        f"/api/appointments/{apt_id}/status",
        json={"new_status": "Checked-In", "changed_by": "STF-001"},
    )
    assert check_in_res.status_code == 200

    # 2. Cancel appointment
    cancel_res = client.post(
        f"/api/appointments/{apt_id}/cancel",
        json={"reason": "Patient Request", "staff_id": "STF-001", "notes": "Patient had to leave early"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "Cancelled"

    # Live queue should no longer have patient Waiting
    queue_res = client.get("/api/queue/live")
    assert queue_res.status_code == 200
    waiting_tokens = [t for t in queue_res.json()["data"] if t["appointment_id"] == apt_id]
    assert len(waiting_tokens) == 0


def test_cannot_cancel_completed_appointment():
    # APT-004 is Completed
    res = client.post(
        "/api/appointments/APT-004/cancel",
        json={"reason": "Patient Request", "staff_id": "STF-001"},
    )
    assert res.status_code == 400
    assert res.json()["success"] is False
    assert "already been completed" in res.json()["message"]


def test_cannot_cancel_already_cancelled_appointment():
    # APT-005 is Cancelled
    res = client.post(
        "/api/appointments/APT-005/cancel",
        json={"reason": "Duplicate Booking", "staff_id": "STF-001"},
    )
    assert res.status_code == 400
    assert res.json()["success"] is False
    assert "already cancelled" in res.json()["message"]


def test_cancel_requires_reason_and_staff_id():
    # Empty reason
    res1 = client.post(
        "/api/appointments/APT-001/cancel",
        json={"reason": "   ", "staff_id": "STF-001"},
    )
    assert res1.status_code == 400
    assert "Cancellation reason is required" in res1.json()["message"]

    # Empty staff_id
    res2 = client.post(
        "/api/appointments/APT-001/cancel",
        json={"reason": "Patient Request", "staff_id": "  "},
    )
    assert res2.status_code == 400
    assert "Staff ID is required" in res2.json()["message"]


def test_cancellation_and_appointment_statistics():
    stats_res = client.get("/api/appointments/statistics/summary")
    assert stats_res.status_code == 200
    stats = stats_res.json()["data"]

    assert stats["total_appointments"] > 0
    assert "completion_rate" in stats
    assert "cancellation_rate" in stats
    assert "no_show_rate" in stats
    assert stats["cancelled_count"] >= 1
    assert stats["released_slots_count"] >= 1
    assert isinstance(stats["reasons_breakdown"], dict)
    assert "Patient Request" in stats["reasons_breakdown"]
