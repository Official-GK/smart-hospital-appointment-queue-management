from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_reschedule_appointment_success_and_audit():
    # 1. Create appointment for Dr. Sarah Smith (DOC-001) on today at 09:00 AM
    today = date.today()
    tomorrow = today + timedelta(days=1)
    today_str = today.isoformat()
    tomorrow_str = tomorrow.isoformat()

    create_payload = {
        "patient_id": "PAT-601",
        "patient_name": "Modify Test Patient",
        "doctor_id": "DOC-001",
        "department_id": "DEP-CARD",
        "appointment_date": today_str,
        "appointment_time": "09:00 AM",
        "priority": "Normal",
        "notes": "Original booking",
    }
    create_res = client.post("/api/appointments", json=create_payload)
    assert create_res.status_code == 201
    apt = create_res.json()["data"]
    apt_id = apt["appointment_id"]
    assert apt["doctor_id"] == "DOC-001"
    assert apt["appointment_time"] == "09:00 AM"

    # Verify old slot is booked
    slots_res_before = client.get(f"/api/appointments/inventory/slots?doctor_id=DOC-001&date={today_str}")
    slot_before = next((s for s in slots_res_before.json()["data"] if s["slot_time"] == "09:00 AM"), None)
    assert slot_before is not None
    assert slot_before["status"] == "BOOKED"

    # 2. Reschedule to Dr. Marcus Johnson (DOC-002, Orthopedics) tomorrow at 02:00 PM
    reschedule_payload = {
        "staff_id": "STF-301",
        "doctor_id": "DOC-002",
        "appointment_date": tomorrow_str,
        "appointment_time": "02:00 PM",
        "reason": "Doctor Availability",
        "notes": "Patient agreed to see orthopedic specialist tomorrow",
    }
    patch_res = client.patch(f"/api/appointments/{apt_id}/reschedule", json=reschedule_payload)
    assert patch_res.status_code == 200
    updated_apt = patch_res.json()["data"]

    # Verify updated appointment details
    assert updated_apt["doctor_id"] == "DOC-002"
    assert updated_apt["doctor_name"] == "Dr. Marcus Johnson"
    assert updated_apt["department_id"] == "DEP-ORTHO"
    assert updated_apt["department_name"] == "Orthopedics"
    assert updated_apt["appointment_date"] == tomorrow_str
    assert updated_apt["appointment_time"] == "02:00 PM"

    # Verify audit trail contains staff ID, old slot details, and new slot details
    history = updated_apt["history"]
    latest_audit = history[-1]
    assert latest_audit["changed_by"] == "STF-301"
    assert latest_audit["old_slot_details"] is not None
    assert latest_audit["old_slot_details"]["doctor_id"] == "DOC-001"
    assert latest_audit["old_slot_details"]["appointment_time"] == "09:00 AM"
    assert latest_audit["new_slot_details"] is not None
    assert latest_audit["new_slot_details"]["doctor_id"] == "DOC-002"
    assert latest_audit["new_slot_details"]["appointment_time"] == "02:00 PM"
    assert "Doctor Availability" in latest_audit["notes"]

    # 3. Verify old slot is released and new slot is booked
    slots_res_after_old = client.get(f"/api/appointments/inventory/slots?doctor_id=DOC-001&date={today_str}")
    slot_old_after = next((s for s in slots_res_after_old.json()["data"] if s["slot_time"] == "09:00 AM"), None)
    assert slot_old_after is not None
    assert slot_old_after["status"] == "RELEASED"

    slots_res_after_new = client.get(f"/api/appointments/inventory/slots?doctor_id=DOC-002&date={tomorrow_str}")
    slot_new_after = next((s for s in slots_res_after_new.json()["data"] if s["slot_time"] == "02:00 PM"), None)
    assert slot_new_after is not None
    assert slot_new_after["status"] == "BOOKED"


def test_slot_conflict_validation():
    # APT-002 is on today at 10:00 AM with Dr. Sarah Smith (DOC-001)
    # Attempting to reschedule another appointment into this exact slot must fail
    reschedule_payload = {
        "staff_id": "STF-101",
        "doctor_id": "DOC-001",
        "appointment_date": date.today().isoformat(),
        "appointment_time": "10:00 AM",
        "reason": "Patient Request",
    }
    # Reschedule APT-001 into APT-002's slot
    res = client.patch("/api/appointments/APT-001/reschedule", json=reschedule_payload)
    assert res.status_code == 400
    assert res.json()["success"] is False
    assert "already booked" in res.json()["message"]


def test_cannot_reschedule_completed_appointment():
    # APT-004 is Completed
    res = client.patch(
        "/api/appointments/APT-004/reschedule",
        json={"staff_id": "STF-101", "appointment_time": "03:00 PM"},
    )
    assert res.status_code == 400
    assert "already been completed" in res.json()["message"]


def test_cannot_reschedule_cancelled_appointment():
    # APT-005 is Cancelled
    res = client.patch(
        "/api/appointments/APT-005/reschedule",
        json={"staff_id": "STF-101", "appointment_time": "03:00 PM"},
    )
    assert res.status_code == 400
    assert "cancelled" in res.json()["message"]


def test_reschedule_requires_staff_id():
    res = client.patch(
        "/api/appointments/APT-001/reschedule",
        json={"staff_id": "  ", "appointment_time": "03:00 PM"},
    )
    assert res.status_code == 400
    assert "Staff ID is required" in res.json()["message"]
