from datetime import date
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_appointments_all_statuses():
    response = client.get("/api/appointments")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    appointments = data["data"]
    assert len(appointments) >= 6

    statuses = {a["status"] for a in appointments}
    expected = {"Scheduled", "Checked-In", "In-Consultation", "Completed", "Cancelled", "No-Show"}
    assert expected.issubset(statuses), f"Missing statuses: {expected - statuses}"


def test_filter_appointments_by_status():
    response = client.get("/api/appointments?status=Completed")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    for apt in data["data"]:
        assert apt["status"] == "Completed"


def test_filter_appointments_by_department():
    response = client.get("/api/appointments?department_id=DEP-CARD")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    for apt in data["data"]:
        assert apt["department_id"] == "DEP-CARD"


def test_filter_appointments_by_doctor():
    response = client.get("/api/appointments?doctor_id=DOC-001")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    for apt in data["data"]:
        assert apt["doctor_id"] == "DOC-001"


def test_filter_appointments_by_date():
    today_str = date.today().isoformat()
    response = client.get(f"/api/appointments?date={today_str}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    for apt in data["data"]:
        assert apt["appointment_date"] == today_str


def test_filter_metadata():
    response = client.get("/api/appointments/metadata/filters")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "Scheduled" in data["statuses"]
    assert len(data["departments"]) >= 5
    assert len(data["doctors"]) >= 5


def test_full_lifecycle_progression_and_audit():
    # 1. Create a new appointment
    create_payload = {
        "patient_id": "PAT-999",
        "patient_name": "Test Patient Lifecycle",
        "doctor_id": "DOC-003",
        "department_id": "DEP-GEN",
        "appointment_date": date.today().isoformat(),
        "appointment_time": "02:00 PM",
        "priority": "Normal",
        "notes": "Testing status transitions",
    }
    create_res = client.post("/api/appointments", json=create_payload)
    assert create_res.status_code == 201
    apt = create_res.json()["data"]
    apt_id = apt["appointment_id"]
    assert apt["status"] == "Scheduled"
    assert apt["timestamps"]["check_in_time"] is None
    assert len(apt["history"]) == 1
    assert apt["history"][0]["to_status"] == "Scheduled"

    # 2. Transition Scheduled -> Checked-In
    check_in_res = client.patch(
        f"/api/appointments/{apt_id}/status",
        json={"new_status": "Checked-In", "changed_by": "Reception Desk 1", "notes": "Patient arrived at clinic"},
    )
    assert check_in_res.status_code == 200
    checked_in_apt = check_in_res.json()["data"]
    assert checked_in_apt["status"] == "Checked-In"
    assert checked_in_apt["token_number"] is not None
    assert checked_in_apt["timestamps"]["check_in_time"] is not None
    assert checked_in_apt["timestamps"]["queue_entry_time"] is not None
    assert len(checked_in_apt["history"]) == 2
    assert checked_in_apt["history"][1]["from_status"] == "Scheduled"
    assert checked_in_apt["history"][1]["to_status"] == "Checked-In"
    assert checked_in_apt["history"][1]["changed_by"] == "Reception Desk 1"

    # Verify Live Queue visibility
    queue_res = client.get("/api/queue/live")
    assert queue_res.status_code == 200
    queue_tokens = queue_res.json()["data"]
    found_in_queue = any(t["appointment_id"] == apt_id and t["status"] == "Waiting" for t in queue_tokens)
    assert found_in_queue, "Checked-in patient must appear in live queue with status 'Waiting'"

    # 3. Transition Checked-In -> In-Consultation
    consult_res = client.patch(
        f"/api/appointments/{apt_id}/status",
        json={"new_status": "In-Consultation", "changed_by": "Dr. Emily Davis", "notes": "Patient called into Room 3"},
    )
    assert consult_res.status_code == 200
    consult_apt = consult_res.json()["data"]
    assert consult_apt["status"] == "In-Consultation"
    assert consult_apt["timestamps"]["consultation_start_time"] is not None
    assert len(consult_apt["history"]) == 3
    assert consult_apt["history"][2]["to_status"] == "In-Consultation"

    # Verify Live Queue status updated to In Consultation
    queue_res2 = client.get("/api/queue/live")
    queue_tokens2 = queue_res2.json()["data"]
    found_consulting = any(t["appointment_id"] == apt_id and t["status"] == "In Consultation" for t in queue_tokens2)
    assert found_consulting, "Live queue must reflect 'In Consultation' status"

    # 4. Transition In-Consultation -> Completed
    complete_res = client.patch(
        f"/api/appointments/{apt_id}/status",
        json={"new_status": "Completed", "changed_by": "Dr. Emily Davis", "notes": "Checkup completed, vitals stable"},
    )
    assert complete_res.status_code == 200
    completed_apt = complete_res.json()["data"]
    assert completed_apt["status"] == "Completed"
    assert completed_apt["timestamps"]["consultation_end_time"] is not None
    assert len(completed_apt["history"]) == 4
    assert completed_apt["history"][3]["to_status"] == "Completed"

    # Verify audit history endpoint
    history_res = client.get(f"/api/appointments/{apt_id}/history")
    assert history_res.status_code == 200
    history_items = history_res.json()["data"]
    assert len(history_items) == 4
    assert [h["to_status"] for h in history_items] == ["Scheduled", "Checked-In", "In-Consultation", "Completed"]


def test_invalid_status_transition_rejected():
    # APT-004 is Completed in seed data; cannot transition to Checked-In
    invalid_res = client.patch(
        "/api/appointments/APT-004/status",
        json={"new_status": "Checked-In", "changed_by": "Hacker"},
    )
    assert invalid_res.status_code == 400
    assert invalid_res.json()["success"] is False
    assert "Cannot transition status" in invalid_res.json()["message"]
