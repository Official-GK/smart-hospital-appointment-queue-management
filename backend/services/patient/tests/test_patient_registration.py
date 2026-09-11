import pytest
from datetime import date
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.services.patient.api.patient_router import router as patient_router
from backend.services.appointment.api.appointment_router import router as appointment_router
from backend.services.patient.services.patient_service import patient_service_instance
from backend.services.appointment.services.appointment_service import appointment_service_instance
from backend.services.queue.services.queue_service import queue_service_instance

# Setup test app
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
app.include_router(appointment_router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_services():
    patient_service_instance.reset()
    appointment_service_instance.repo.reset()
    queue_service_instance._tokens.clear()
    queue_service_instance._token_counter = 100


def test_register_new_patient_success():
    """
    Verify front-desk staff can register a new patient with Name, Age, Gender, Contact Number, Address.
    System automatically generates a unique Patient ID (PAT-009).
    """
    payload = {
        "first_name": "Samantha",
        "last_name": "Hayes",
        "age": 28,
        "gender": "Female",
        "contact_number": "+1-555-0199",
        "address": "742 Evergreen Terrace, Springfield",
    }
    response = client.post("/api/patients", json=payload)
    assert response.status_code == 201
    data = response.json()["data"]

    assert data["patient_id"] == "PAT-009"
    assert data["patient_name"] == "Samantha Hayes"
    assert data["first_name"] == "Samantha"
    assert data["last_name"] == "Hayes"
    assert data["age"] == 28
    assert data["gender"] == "Female"
    assert data["phone"] == "+1-555-0199"
    assert data["address"] == "742 Evergreen Terrace, Springfield"
    assert data["status"] == "Registered"
    assert data["date_of_birth"] is not None


def test_register_with_full_name_and_dob():
    """
    Verify registration accepting combined name and date_of_birth.
    """
    payload = {
        "name": "Marcus Aurelius",
        "date_of_birth": "1994-06-15",
        "gender": "Male",
        "phone": "+1-555-0198",
        "address": "100 Forum Way, Rome",
    }
    response = client.post("/api/patients", json=payload)
    assert response.status_code == 201
    data = response.json()["data"]

    assert data["patient_id"] == "PAT-009"
    assert data["first_name"] == "Marcus"
    assert data["last_name"] == "Aurelius"
    assert data["patient_name"] == "Marcus Aurelius"
    assert data["age"] is not None
    assert data["phone"] == "+1-555-0198"


def test_duplicate_registration_by_contact_number_rejected():
    """
    Verify duplicate patient registration is blocked based on contact number (HTTP 409 Conflict).
    PAT-001 has phone '+1-555-0101'.
    """
    # Attempt duplicate with exact formatted phone
    payload = {
        "first_name": "Duplicate",
        "last_name": "Patient",
        "age": 30,
        "gender": "Male",
        "contact_number": "+1-555-0101",
        "address": "999 Imposter Lane",
    }
    response = client.post("/api/patients", json=payload)
    assert response.status_code == 409
    body = response.json()
    error_text = body.get("message", "") or str(body.get("error", ""))
    assert "already registered" in error_text.lower()
    assert "PAT-001" in error_text

    # Attempt duplicate with unformatted digits
    payload_digits = {
        "first_name": "Another",
        "last_name": "Imposter",
        "age": 32,
        "contact_number": "15550101",
    }
    response2 = client.post("/api/patients", json=payload_digits)
    assert response2.status_code == 409
    body2 = response2.json()
    error_text2 = body2.get("message", "") or str(body2.get("error", ""))
    assert "PAT-001" in error_text2


def test_duplicate_registration_by_identifier_rejected():
    """
    Verify duplicate patient registration is blocked when an identifier matches an existing patient.
    """
    payload = {
        "first_name": "Cloned",
        "last_name": "Identifier",
        "age": 40,
        "contact_number": "+1-555-0950",
        "identifier": "PAT-002",
    }
    response = client.post("/api/patients", json=payload)
    assert response.status_code == 409
    body = response.json()
    error_text = body.get("message", "") or str(body.get("error", ""))
    assert "already registered" in error_text.lower()
    assert "PAT-002" in error_text


def test_preflight_duplicate_check_endpoint():
    """
    Verify GET /api/patients/check-duplicate returns accurate conflict statuses.
    """
    # Check existing phone
    res_existing = client.get("/api/patients/check-duplicate?contact_number=+1-555-0101")
    assert res_existing.status_code == 200
    data = res_existing.json()["data"]
    assert data["is_duplicate"] is True
    assert data["existing_patient_id"] == "PAT-001"
    assert data["matched_field"] == "contact_number"

    # Check non-existing phone
    res_new = client.get("/api/patients/check-duplicate?contact_number=+1-555-9876")
    assert res_new.status_code == 200
    data_new = res_new.json()["data"]
    assert data_new["is_duplicate"] is False
    assert data_new["existing_patient_id"] is None

    # Check existing identifier
    res_id = client.get("/api/patients/check-duplicate?identifier=PAT-003")
    assert res_id.status_code == 200
    data_id = res_id.json()["data"]
    assert data_id["is_duplicate"] is True
    assert data_id["existing_patient_id"] == "PAT-003"


def test_registered_patient_immediately_available_for_check_in():
    """
    Acceptance criteria: Registered patient records are immediately available for check-in.
    Register a patient, then immediately execute arrival check-in with the new Patient ID.
    """
    # 1. Register new patient
    reg_payload = {
        "first_name": "Lucas",
        "last_name": "Vance",
        "age": 35,
        "gender": "Male",
        "contact_number": "+1-555-0210",
        "address": "400 Skyline Blvd",
    }
    reg_res = client.post("/api/patients", json=reg_payload)
    assert reg_res.status_code == 201
    new_patient_id = reg_res.json()["data"]["patient_id"]
    assert new_patient_id == "PAT-009"

    # 2. Immediately execute walk-in check-in for the newly registered patient
    checkin_payload = {
        "patient_id": new_patient_id,
        "doctor_id": "DOC-001",
        "department_id": "DEP-CARD",
        "priority": "Normal",
        "is_walk_in": True,
        "notes": "Immediate walk-in check-in post registration",
    }
    checkin_res = client.post("/api/patients/check-in", json=checkin_payload)
    assert checkin_res.status_code == 200
    receipt = checkin_res.json()["data"]

    assert receipt["patient_id"] == new_patient_id
    assert receipt["patient_name"] == "Lucas Vance"
    assert receipt["status"] == "Checked-In"
    assert receipt["token_number"] is not None
    assert receipt["queue_position"] >= 1

    # 3. Verify patient's status is updated in repository
    patient_res = client.get(f"/api/patients/{new_patient_id}")
    assert patient_res.status_code == 200
    assert patient_res.json()["data"]["status"] == "Checked-In"


def test_registered_patient_immediately_available_for_appointment_booking():
    """
    Acceptance criteria: Registered patient records are immediately available for appointment booking.
    Register a patient, then immediately schedule an appointment for them.
    """
    # 1. Register new patient
    reg_payload = {
        "first_name": "Nora",
        "last_name": "Allen",
        "age": 24,
        "gender": "Female",
        "contact_number": "+1-555-0211",
        "address": "500 Central City Way",
    }
    reg_res = client.post("/api/patients", json=reg_payload)
    assert reg_res.status_code == 201
    patient_id = reg_res.json()["data"]["patient_id"]

    # 2. Immediately book appointment
    apt_payload = {
        "patient_id": patient_id,
        "patient_name": "Nora Allen",
        "doctor_id": "DOC-002",
        "department_id": "DEP-CARD",
        "appointment_date": "2026-09-15",
        "appointment_time": "10:30 AM",
        "priority": "Normal",
        "notes": "Routine follow up for newly registered patient",
        "staff_id": "Front-Desk Staff",
    }
    apt_res = client.post("/api/appointments", json=apt_payload)
    assert apt_res.status_code == 201
    apt_data = apt_res.json()["data"]

    assert apt_data["patient_id"] == patient_id
    assert apt_data["patient_name"] == "Nora Allen"
    assert apt_data["status"] == "Scheduled"

    # 3. Verify in patient profile
    profile_res = client.get(f"/api/patients/{patient_id}/profile")
    assert profile_res.status_code == 200
    profile_data = profile_res.json()["data"]
    assert len(profile_data["active_appointments"]) == 1
    assert profile_data["active_appointments"][0]["appointment_id"] == apt_data["appointment_id"]


def test_registration_validation_errors():
    """
    Verify validation fails when mandatory demographic fields are missing.
    """
    # Missing phone/contact number
    res_no_phone = client.post("/api/patients", json={"first_name": "Incomplete", "last_name": "User"})
    assert res_no_phone.status_code == 422

    # Missing name
    res_no_name = client.post("/api/patients", json={"contact_number": "+1-555-9999"})
    assert res_no_name.status_code == 422
