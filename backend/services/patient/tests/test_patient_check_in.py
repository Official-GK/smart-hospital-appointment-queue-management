import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI

from backend.services.patient.api.patient_router import router as patient_router
from backend.services.patient.services.patient_service import patient_service_instance
from backend.services.patient.schemas.patient_schemas import (
    PatientCheckInRequest,
    PatientStatus,
)
from backend.services.appointment.services.appointment_service import appointment_service_instance
from backend.services.appointment.schemas.appointment_schemas import AppointmentStatus
from backend.services.queue.services.queue_service import queue_service_instance
from backend.services.queue.schemas.queue_schemas import QueuePriority

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# Create isolated FastAPI test app for patient router
app = FastAPI()

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail if isinstance(exc.detail, str) else "Request failed",
            "error": exc.detail if not isinstance(exc.detail, str) else {"detail": exc.detail},
        },
    )

app.include_router(patient_router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_services():
    """Reset repositories before each test"""
    patient_service_instance.reset()
    appointment_service_instance.repo.reset()
    queue_service_instance._tokens.clear()
    queue_service_instance._token_counter = 100


def test_check_in_scheduled_appointment_success():
    """
    Test checking in a patient for a scheduled appointment:
    - Arrival timestamp is recorded
    - Patient and appointment status updated to Checked-In
    - Patient immediately added to active doctor/department queue with token
    """
    # APT-001 is Scheduled for James Wilson
    apt_before = appointment_service_instance.get_appointment_by_id("APT-001")
    assert apt_before.status == AppointmentStatus.SCHEDULED
    assert apt_before.timestamps.check_in_time is None

    response = client.post(
        "/api/patients/check-in",
        json={
            "appointment_id": "APT-001",
            "patient_id": "PAT-001",
            "notes": "Arrived on time at reception",
            "checked_in_by": "Receptionist Mary",
        },
    )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    receipt = res_data["data"]

    assert receipt["appointment_id"] == "APT-001"
    assert receipt["patient_id"] == "PAT-001"
    assert receipt["patient_name"] == "James Wilson"
    assert receipt["status"] == "Checked-In"
    assert receipt["arrival_time"] is not None
    assert receipt["token_number"] is not None
    assert receipt["queue_position"] >= 1
    assert receipt["estimated_wait_minutes"] is not None
    assert receipt["is_walk_in"] is False

    # Verify appointment service updated check_in_time
    apt_after = appointment_service_instance.get_appointment_by_id("APT-001")
    assert apt_after.status == AppointmentStatus.CHECKED_IN
    assert apt_after.timestamps.check_in_time is not None

    # Verify patient repository updated status
    patient = patient_service_instance.get_patient_by_id("PAT-001")
    assert patient.status == PatientStatus.CHECKED_IN
    assert patient.last_arrival_time is not None

    # Verify patient is in active queue
    live_queue = queue_service_instance.get_live_queue(doctor_id=apt_after.doctor_id)
    queued_item = next((q for q in live_queue if q.appointment_id == "APT-001"), None)
    assert queued_item is not None
    assert queued_item.patient_name == "James Wilson"
    assert queued_item.status.value == "Waiting"


def test_check_in_walk_in_patient_success():
    """
    Test walk-in patient check-in:
    - Automatically creates/registers walk-in patient
    - Records arrival timestamp
    - Generates active queue token immediately
    - Enqueues into active doctor queue
    """
    response = client.post(
        "/api/patients/check-in",
        json={
            "patient_name": "Arthur Dent",
            "phone": "+1-555-4242",
            "department_id": "DEP-GEN",
            "doctor_id": "DOC-001",
            "priority": "Normal",
            "is_walk_in": True,
            "notes": "Walk-in headache consultation",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]

    assert data["patient_name"] == "Arthur Dent"
    assert data["status"] == "Checked-In"
    assert data["is_walk_in"] is True
    assert data["token_number"] is not None
    assert data["doctor_id"] == "DOC-001"
    assert data["queue_position"] >= 1
    assert data["arrival_time"] is not None

    # Verify patient is in active queue
    live_queue = queue_service_instance.get_live_queue(doctor_id="DOC-001")
    queued = next((q for q in live_queue if q.patient_name == "Arthur Dent"), None)
    assert queued is not None
    assert queued.is_walk_in is True
    assert queued.priority == QueuePriority.NORMAL


def test_check_in_walk_in_emergency_priority():
    """
    Test emergency walk-in check-in:
    - Places patient in active queue with highest Emergency priority
    """
    response = client.post(
        "/api/patients/check-in",
        json={
            "patient_name": "Sarah Connor",
            "phone": "+1-555-9999",
            "department_id": "DEP-CARD",
            "doctor_id": "DOC-001",
            "priority": "Emergency",
            "is_walk_in": True,
            "notes": "Acute chest pain",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["priority"] == "Emergency"

    # Verify queue priority
    live_queue = queue_service_instance.get_live_queue(doctor_id="DOC-001")
    emergency_item = next((q for q in live_queue if q.patient_name == "Sarah Connor"), None)
    assert emergency_item is not None
    assert emergency_item.priority == QueuePriority.EMERGENCY


def test_prevent_double_check_in():
    """
    Test that checking in an already checked-in patient fails with 400
    """
    # APT-002 is already Checked-In in demo data
    response = client.post(
        "/api/patients/check-in",
        json={
            "appointment_id": "APT-002",
            "patient_id": "PAT-002",
        },
    )
    assert response.status_code == 400
    assert "already checked in" in response.json()["message"].lower()


def test_prevent_check_in_completed_or_cancelled():
    """
    Test that checking in a completed or cancelled appointment fails with 400
    """
    # APT-004 is Completed
    res_completed = client.post(
        "/api/patients/check-in",
        json={"appointment_id": "APT-004", "patient_id": "PAT-004"},
    )
    assert res_completed.status_code == 400

    # APT-005 is Cancelled
    res_cancelled = client.post(
        "/api/patients/check-in",
        json={"appointment_id": "APT-005", "patient_id": "PAT-005"},
    )
    assert res_cancelled.status_code == 400


def test_get_eligible_check_ins():
    """
    Test retrieving scheduled appointments ready for front-desk check-in
    """
    response = client.get("/api/patients/check-in/eligible")
    assert response.status_code == 200
    eligible_list = response.json()["data"]
    assert len(eligible_list) > 0

    # All returned items must have status Scheduled and can_check_in True
    for item in eligible_list:
        assert item["status"] == "Scheduled"
        assert item["can_check_in"] is True
        assert "appointment_id" in item
        assert "patient_name" in item


def test_patient_demographics_and_search():
    """
    Test patient search and profile retrieval
    """
    # List all
    res_all = client.get("/api/patients")
    assert res_all.status_code == 200
    assert len(res_all.json()["data"]) >= 6

    # Search by name
    res_search = client.get("/api/patients?query=Wilson")
    assert res_search.status_code == 200
    results = res_search.json()["data"]
    assert len(results) == 1
    assert results[0]["patient_id"] == "PAT-001"

    # Get by ID
    res_id = client.get("/api/patients/PAT-001")
    assert res_id.status_code == 200
    assert res_id.json()["data"]["patient_name"] == "James Wilson"
