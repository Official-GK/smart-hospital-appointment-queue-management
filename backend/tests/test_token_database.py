from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.database.demo_data import (
    DEFAULT_SLOTS,
    DEPARTMENTS,
    DOCTORS,
    get_demo_appointments,
    get_demo_released_slots,
)
from backend.database.token_fetcher import (
    fetch_live_queue_tokens,
    fetch_token_by_appointment,
    fetch_token_by_id,
    fetch_tokens_by_appointments,
    fetch_tokens_by_patient,
    save_token,
)
from backend.main import app

client = TestClient(app)


def test_demo_data_centralization_and_no_demo_tokens():
    """
    Verify that all demo data is sourced from database.demo_data
    and that seed appointments contain NO hardcoded demo tokens (token_id=None, token_number=None).
    """
    assert len(DEPARTMENTS) == 5
    assert len(DOCTORS) == 5
    assert len(DEFAULT_SLOTS) >= 10

    seed_apts = get_demo_appointments()
    assert len(seed_apts) >= 6

    # Verify no appointment has hardcoded demo tokens
    for apt_id, apt in seed_apts.items():
        assert apt.token_id is None, f"Appointment {apt_id} must have token_id=None"
        assert apt.token_number is None, f"Appointment {apt_id} must have token_number=None"


def test_unconfigured_tokens_return_no_token_on_api():
    """
    Verify that when appointments do not have a configured token in PostgreSQL,
    the API returns token_number=None so that the frontend renders 'No Token'.
    """
    response = client.get("/api/appointments")
    assert response.status_code == 200
    data = response.json()["data"]

    # APT-001 is unconfigured in PostgreSQL, so token_number and token_id are None
    scheduled_apt = next((a for a in data if a["appointment_id"] == "APT-001"), None)
    assert scheduled_apt is not None
    assert scheduled_apt["token_number"] is None
    assert scheduled_apt["token_id"] is None

    # APT-004 is unconfigured in PostgreSQL, so token_number and token_id are None
    completed_apt = next((a for a in data if a["appointment_id"] == "APT-004"), None)
    assert completed_apt is not None
    assert completed_apt["token_number"] is None
    assert completed_apt["token_id"] is None


def test_database_offline_handled_gracefully():
    """
    Verify that when PostgreSQL connection fails, all database token fetcher functions
    handle the error gracefully using try...except and return safe empty/None values.
    """
    with patch("backend.database.connection.psycopg2.connect", side_effect=Exception("Database connection refused")):
        # All calls must return gracefully without throwing exceptions
        assert fetch_token_by_appointment("APT-001") is None
        assert fetch_tokens_by_appointments(["APT-001", "APT-002"]) == {}
        assert fetch_token_by_id("TOK-101") is None
        assert fetch_tokens_by_patient("PAT-001") == []
        assert fetch_live_queue_tokens() == []
        assert save_token({"token_id": "TOK-999", "token_number": "T-999"}) is False


def test_database_token_fetch_matching_technical_contracts():
    """
    Verify that when PostgreSQL returns a token record matching TECHNICAL_CONTRACTS.md Section 7,
    it is correctly formatted and parsed by the fetchers.
    TECHNICAL_CONTRACTS.md Section 7:
    token_id, token_number, patient_id, doctor_id, department_id, priority, status, created_at
    """
    mock_row = {
        "token_id": "TOK-777",
        "token_number": "T-777",
        "appointment_id": "APT-001",
        "patient_id": "PAT-001",
        "patient_name": "James Wilson",
        "doctor_id": "DOC-001",
        "doctor_name": "Dr. Sarah Smith",
        "department_id": "DEP-CARD",
        "department_name": "Cardiology",
        "priority": "Normal",
        "status": "Waiting",
        "created_at": datetime.utcnow(),
        "queue_entry_time": datetime.utcnow(),
        "called_time": None,
        "consultation_start_time": None,
        "consultation_end_time": None,
        "estimated_wait_minutes": 10,
    }

    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = mock_row
    mock_cur.fetchall.return_value = [mock_row]

    with patch("backend.database.token_fetcher.get_cursor") as mock_get_cursor:
        mock_get_cursor.return_value.__enter__.return_value = mock_cur

        token = fetch_token_by_appointment("APT-001")
        assert token is not None
        assert token["token_id"] == "TOK-777"
        assert token["token_number"] == "T-777"
        assert token["patient_id"] == "PAT-001"
        assert token["doctor_id"] == "DOC-001"
        assert token["department_id"] == "DEP-CARD"
        assert token["priority"] == "Normal"
        assert token["status"] == "Waiting"
        assert "created_at" in token


def test_api_dynamically_binds_database_tokens():
    """
    Verify that when PostgreSQL contains configured tokens, the API endpoint
    /api/appointments binds token_id and token_number to the appointment response.
    """
    mock_tokens_map = {
        "APT-001": {
            "token_id": "TOK-888",
            "token_number": "T-888",
            "appointment_id": "APT-001",
            "patient_id": "PAT-001",
            "doctor_id": "DOC-001",
            "department_id": "DEP-CARD",
            "priority": "Normal",
            "status": "Waiting",
            "created_at": datetime.utcnow(),
        }
    }

    with patch("backend.services.appointment.services.appointment_service.fetch_tokens_by_appointments", return_value=mock_tokens_map):
        response = client.get("/api/appointments")
        assert response.status_code == 200
        data = response.json()["data"]
        apt1 = next((a for a in data if a["appointment_id"] == "APT-001"), None)
        assert apt1 is not None
        assert apt1["token_id"] == "TOK-888"
        assert apt1["token_number"] == "T-888"
