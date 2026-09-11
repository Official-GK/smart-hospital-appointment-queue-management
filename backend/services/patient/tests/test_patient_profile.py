import pytest
from datetime import date
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.services.patient.api.patient_router import router as patient_router
from backend.services.patient.services.patient_service import patient_service_instance
from backend.services.appointment.services.appointment_service import appointment_service_instance
from backend.services.queue.services.queue_service import queue_service_instance

# Create isolated test app with standard error handler
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


def test_search_patient_by_id_name_phone():
    """
    Test staff searching patient profiles by ID, Name, or Phone Number
    """
    # 1. Search by Patient ID
    res_id = client.get("/api/patients?query=PAT-002")
    assert res_id.status_code == 200
    data_id = res_id.json()["data"]
    assert len(data_id) == 1
    assert data_id[0]["patient_name"] == "Michael Chen"

    # 2. Search by Name (case-insensitive substring)
    res_name = client.get("/api/patients?query=rodriguez")
    assert res_name.status_code == 200
    data_name = res_name.json()["data"]
    assert len(data_name) == 1
    assert data_name[0]["patient_id"] == "PAT-003"

    # 3. Search by Phone Number
    res_phone = client.get("/api/patients?query=0105")
    assert res_phone.status_code == 200
    data_phone = res_phone.json()["data"]
    assert len(data_phone) == 1
    assert data_phone[0]["patient_name"] == "Sophia Martinez"


def test_get_patient_profile_demographics_and_active_appointments():
    """
    Test profile view displaying demographics and active appointments
    """
    response = client.get("/api/patients/PAT-001/profile", headers={"X-User-Role": "Staff"})
    assert response.status_code == 200
    profile = response.json()["data"]

    # Demographics
    assert profile["patient_id"] == "PAT-001"
    assert profile["patient_name"] == "James Wilson"
    assert profile["gender"] == "Male"
    assert profile["phone"] == "+1-555-0101"
    assert profile["address"] == "124 Oak Street, Springfield"
    assert profile["age"] is not None
    assert profile["age"] >= 35
    assert profile["is_masked"] is False

    # Active Appointments (APT-001 is Scheduled)
    active = profile["active_appointments"]
    assert len(active) >= 1
    apt1 = next((a for a in active if a["appointment_id"] == "APT-001"), None)
    assert apt1 is not None
    assert apt1["status"] == "Scheduled"
    assert apt1["doctor_name"] == "Dr. Sarah Smith"
    assert apt1["department_name"] == "Cardiology"
    assert apt1["booking_time"] is not None


def test_get_patient_profile_past_visit_history_and_timestamps():
    """
    Test profile view displaying past visit history with full operational timestamps
    """
    # PAT-004 (Robert Taylor) has Completed appointment APT-004 in demo data
    response = client.get("/api/patients/PAT-004/profile", headers={"X-User-Role": "Doctor"})
    assert response.status_code == 200
    profile = response.json()["data"]

    visits = profile["visit_history"]
    assert len(visits) >= 1
    apt4 = next((v for v in visits if v["appointment_id"] == "APT-004"), None)
    assert apt4 is not None
    assert apt4["status"] == "Completed"
    assert apt4["booking_time"] is not None
    assert apt4["check_in_time"] is not None
    assert apt4["consultation_start_time"] is not None
    assert apt4["completion_time"] is not None


def test_update_patient_demographics_and_audit_logging():
    """
    Test updating patient demographic and contact details with audit logging
    """
    update_payload = {
        "phone": "+1-555-8888",
        "address": "999 Pinecrest Avenue, Springfield",
        "updated_by": "Supervisor Clara",
        "notes": "Patient relocated to new apartment",
    }

    # 1. Execute update
    res_update = client.put("/api/patients/PAT-001", json=update_payload)
    assert res_update.status_code == 200
    updated = res_update.json()["data"]
    assert updated["phone"] == "+1-555-8888"
    assert updated["address"] == "999 Pinecrest Avenue, Springfield"

    # 2. Verify audit trail generated
    res_audit = client.get("/api/patients/PAT-001/audit")
    assert res_audit.status_code == 200
    audits = res_audit.json()["data"]
    assert len(audits) == 2

    # Check phone audit record
    phone_audit = next((a for a in audits if a["field_name"] == "phone"), None)
    assert phone_audit is not None
    assert phone_audit["old_value"] == "+1-555-0101"
    assert phone_audit["new_value"] == "+1-555-8888"
    assert phone_audit["changed_by"] == "Supervisor Clara"
    assert phone_audit["notes"] == "Patient relocated to new apartment"

    # Check address audit record
    addr_audit = next((a for a in audits if a["field_name"] == "address"), None)
    assert addr_audit is not None
    assert addr_audit["old_value"] == "124 Oak Street, Springfield"
    assert addr_audit["new_value"] == "999 Pinecrest Avenue, Springfield"

    # 3. Verify audit trail appears in full profile
    res_prof = client.get("/api/patients/PAT-001/profile", headers={"X-User-Role": "Staff"})
    profile_audits = res_prof.json()["data"]["audit_trail"]
    assert len(profile_audits) == 2


def test_prevent_duplicate_phone_update():
    """
    Test updating patient with an existing phone number returns 409 Conflict
    """
    # PAT-002 has phone +1-555-0102
    response = client.put(
        "/api/patients/PAT-001",
        json={"phone": "+1-555-0102"},
    )
    assert response.status_code == 409
    assert "already registered" in response.json()["message"].lower()


def test_role_based_privacy_data_masking():
    """
    Test that profile viewing respects role-based data masking and privacy guidelines
    """
    # 1. Masked view when explicitly requested via query parameter
    res_masked = client.get("/api/patients/PAT-001/profile?mask_sensitive=true", headers={"X-User-Role": "Staff"})
    assert res_masked.status_code == 200
    prof_masked = res_masked.json()["data"]
    assert prof_masked["is_masked"] is True
    assert "***" in prof_masked["phone"]
    assert "***" in prof_masked["address"]

    # 2. Masked view for unauthorized or public roles
    res_guest = client.get("/api/patients/PAT-001/profile", headers={"X-User-Role": "PublicKiosk"})
    assert res_guest.status_code == 200
    prof_guest = res_guest.json()["data"]
    assert prof_guest["is_masked"] is True
    assert "***" in prof_guest["phone"]

    # 3. Unmasked view for authorized staff (e.g. Doctor or Staff)
    res_doctor = client.get("/api/patients/PAT-001/profile", headers={"X-User-Role": "Doctor"})
    assert res_doctor.status_code == 200
    prof_doc = res_doctor.json()["data"]
    assert prof_doc["is_masked"] is False
    assert prof_doc["phone"] == "+1-555-0101"
    assert prof_doc["address"] == "124 Oak Street, Springfield"
