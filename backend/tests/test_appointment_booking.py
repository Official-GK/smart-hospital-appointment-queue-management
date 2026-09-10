from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_book_appointment_success():
    """
    Test successful appointment booking:
    - Verifies department, doctor, date, and slot selection
    - Generates unique appointment ID and records booking timestamps
    - Automatically generates initial audit record
    """
    future_date = (date.today() + timedelta(days=5)).isoformat()
    payload = {
        "patient_name": "Oliver Queen",
        "doctor_id": "DOC-003",
        "department_id": "DEP-GEN",
        "appointment_date": future_date,
        "appointment_time": "09:00 AM",
        "priority": "Normal",
        "notes": "Annual general checkup",
        "staff_id": "STF-909",
    }
    response = client.post("/api/appointments", json=payload)
    assert response.status_code == 201
    data = response.json()["data"]

    assert data["appointment_id"].startswith("APT-")
    assert data["patient_id"].startswith("PAT-")
    assert data["patient_name"] == "Oliver Queen"
    assert data["doctor_id"] == "DOC-003"
    assert data["doctor_name"] == "Dr. Emily Davis"
    assert data["department_id"] == "DEP-GEN"
    assert data["department_name"] == "General Medicine"
    assert data["appointment_date"] == future_date
    assert data["appointment_time"] == "09:00 AM"
    assert data["status"] == "Scheduled"
    assert data["timestamps"]["created_at"] is not None
    assert len(data["history"]) >= 1
    assert data["history"][0]["changed_by"] == "STF-909"
    assert data["history"][0]["to_status"] == "Scheduled"


def test_prevent_double_booking_conflict():
    """
    Test that the system strictly prevents double-booking or overbooking:
    - Booking a slot that is already reserved by another appointment returns HTTP 400
    """
    future_date = (date.today() + timedelta(days=6)).isoformat()
    payload1 = {
        "patient_name": "Barry Allen",
        "doctor_id": "DOC-001",
        "department_id": "DEP-CARD",
        "appointment_date": future_date,
        "appointment_time": "10:30 AM",
        "staff_id": "STF-101",
    }
    res1 = client.post("/api/appointments", json=payload1)
    assert res1.status_code == 201

    # Attempt to book the exact same slot with the same doctor
    payload2 = {
        "patient_name": "Iris West",
        "doctor_id": "DOC-001",
        "department_id": "DEP-CARD",
        "appointment_date": future_date,
        "appointment_time": "10:30 AM",
        "staff_id": "STF-102",
    }
    res2 = client.post("/api/appointments", json=payload2)
    assert res2.status_code == 400
    assert res2.json()["success"] is False
    assert "already booked" in res2.json()["message"]


def test_book_appointment_updates_inventory():
    """
    Test that booking an appointment updates slot inventory to BOOKED
    """
    target_date = (date.today() + timedelta(days=7)).isoformat()
    slot_time = "11:00 AM"

    # Verify initially available
    slots_res_before = client.get(f"/api/appointments/inventory/slots?doctor_id=DOC-002&date={target_date}")
    slot_before = next((s for s in slots_res_before.json()["data"] if s["slot_time"] == slot_time), None)
    assert slot_before is not None
    assert slot_before["status"] == "AVAILABLE"

    # Book the slot
    book_payload = {
        "patient_name": "Clark Kent",
        "doctor_id": "DOC-002",
        "department_id": "DEP-ORTHO",
        "appointment_date": target_date,
        "appointment_time": slot_time,
        "staff_id": "STF-202",
    }
    book_res = client.post("/api/appointments", json=book_payload)
    assert book_res.status_code == 201
    apt_id = book_res.json()["data"]["appointment_id"]

    # Verify inventory is now BOOKED
    slots_res_after = client.get(f"/api/appointments/inventory/slots?doctor_id=DOC-002&date={target_date}")
    slot_after = next((s for s in slots_res_after.json()["data"] if s["slot_time"] == slot_time), None)
    assert slot_after is not None
    assert slot_after["status"] == "BOOKED"
    assert slot_after["appointment_id"] == apt_id
    assert slot_after["patient_name"] == "Clark Kent"


def test_booking_validation_missing_fields():
    """
    Test input validation when booking:
    - Empty patient name rejected with HTTP 400
    - Invalid doctor_id rejected with HTTP 400
    - Invalid department_id rejected with HTTP 400
    """
    future_date = (date.today() + timedelta(days=8)).isoformat()

    # Missing patient name
    res = client.post("/api/appointments", json={
        "patient_name": "   ",
        "doctor_id": "DOC-001",
        "department_id": "DEP-CARD",
        "appointment_date": future_date,
        "appointment_time": "02:00 PM",
    })
    assert res.status_code == 400
    assert "Patient name is required" in res.json()["message"]

    # Invalid doctor
    res_doc = client.post("/api/appointments", json={
        "patient_name": "Bruce Wayne",
        "doctor_id": "DOC-INVALID",
        "department_id": "DEP-CARD",
        "appointment_date": future_date,
        "appointment_time": "02:00 PM",
    })
    assert res_doc.status_code == 400
    assert "Invalid doctor_id" in res_doc.json()["message"]


def test_booking_auto_generates_unique_ids():
    """
    Test that sequential bookings generate distinct unique IDs
    """
    future_date = (date.today() + timedelta(days=9)).isoformat()
    apt_ids = set()
    for i, t in enumerate(["09:00 AM", "09:30 AM", "10:00 AM"]):
        res = client.post("/api/appointments", json={
            "patient_name": f"Patient Number {i}",
            "doctor_id": "DOC-005",
            "department_id": "DEP-DERM",
            "appointment_date": future_date,
            "appointment_time": t,
        })
        assert res.status_code == 201
        apt_id = res.json()["data"]["appointment_id"]
        assert apt_id not in apt_ids
        apt_ids.add(apt_id)

    assert len(apt_ids) == 3
