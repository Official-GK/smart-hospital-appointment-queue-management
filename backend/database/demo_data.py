"""
Centralized Demo / Seed Data Repository for the Hospital System.
All demo data (departments, doctors, slots, seed appointments) resides strictly
in this single database module file.

NOTE: Tokens are NOT hardcoded here. Real tokens must be configured in PostgreSQL
and fetched dynamically according to TECHNICAL_CONTRACTS.md Section 7.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List

DEPARTMENTS: List[Dict[str, str]] = [
    {"department_id": "DEP-CARD", "department_name": "Cardiology", "avg_consultation_time": 30},
    {"department_id": "DEP-ORTHO", "department_name": "Orthopedics", "avg_consultation_time": 45},
    {"department_id": "DEP-GEN", "department_name": "General Medicine", "avg_consultation_time": 15},
    {"department_id": "DEP-PED", "department_name": "Pediatrics", "avg_consultation_time": 20},
    {"department_id": "DEP-DERM", "department_name": "Dermatology", "avg_consultation_time": 20},
]

DOCTORS: List[Dict[str, str]] = [
    {"doctor_id": "DOC-001", "doctor_name": "Dr. Sarah Smith", "department_id": "DEP-CARD", "department_name": "Cardiology"},
    {"doctor_id": "DOC-002", "doctor_name": "Dr. Marcus Johnson", "department_id": "DEP-ORTHO", "department_name": "Orthopedics"},
    {"doctor_id": "DOC-003", "doctor_name": "Dr. Emily Davis", "department_id": "DEP-GEN", "department_name": "General Medicine"},
    {"doctor_id": "DOC-004", "doctor_name": "Dr. Michael Brown", "department_id": "DEP-PED", "department_name": "Pediatrics"},
    {"doctor_id": "DOC-005", "doctor_name": "Dr. Priya Patel", "department_id": "DEP-DERM", "department_name": "Dermatology"},
    # Weekend Coverage Doctors
    {"doctor_id": "DOC-006", "doctor_name": "Dr. William Vance", "department_id": "DEP-CARD", "department_name": "Cardiology"},
    {"doctor_id": "DOC-007", "doctor_name": "Dr. Olivia Martinez", "department_id": "DEP-ORTHO", "department_name": "Orthopedics"},
    {"doctor_id": "DOC-008", "doctor_name": "Dr. Daniel Lee", "department_id": "DEP-GEN", "department_name": "General Medicine"},
    {"doctor_id": "DOC-009", "doctor_name": "Dr. Sophia Carter", "department_id": "DEP-PED", "department_name": "Pediatrics"},
    {"doctor_id": "DOC-010", "doctor_name": "Dr. Lucas Bennett", "department_id": "DEP-DERM", "department_name": "Dermatology"},
]

DEFAULT_SLOTS: List[str] = [
    "08:45 AM",
    "09:00 AM",
    "09:30 AM",
    "10:00 AM",
    "10:15 AM",
    "10:30 AM",
    "11:00 AM",
    "11:30 AM",
    "02:00 PM",
    "02:30 PM",
    "03:00 PM",
    "03:30 PM",
    "04:00 PM",
]

# Centralized seed demographic records adhering to TECHNICAL_CONTRACTS.md Section 7
DEMO_PATIENTS: List[Dict[str, Any]] = [
    {
        "patient_id": "PAT-001",
        "first_name": "James",
        "last_name": "Wilson",
        "patient_name": "James Wilson",
        "date_of_birth": date(1985, 4, 12),
        "age": 41,
        "gender": "Male",
        "phone": "+1-555-0101",
        "address": "124 Oak Street, Springfield",
        "status": "Registered",
    },
    {
        "patient_id": "PAT-002",
        "first_name": "Michael",
        "last_name": "Chen",
        "patient_name": "Michael Chen",
        "date_of_birth": date(1990, 8, 23),
        "age": 36,
        "gender": "Male",
        "phone": "+1-555-0102",
        "address": "452 Elm Street, Springfield",
        "status": "Checked-In",
    },
    {
        "patient_id": "PAT-003",
        "first_name": "Elena",
        "last_name": "Rodriguez",
        "patient_name": "Elena Rodriguez",
        "date_of_birth": date(1978, 11, 5),
        "age": 47,
        "gender": "Female",
        "phone": "+1-555-0103",
        "address": "789 Pine Road, Springfield",
        "status": "In-Consultation",
    },
    {
        "patient_id": "PAT-004",
        "first_name": "Robert",
        "last_name": "Taylor",
        "patient_name": "Robert Taylor",
        "date_of_birth": date(1965, 2, 17),
        "age": 61,
        "gender": "Male",
        "phone": "+1-555-0104",
        "address": "321 Maple Avenue, Springfield",
        "status": "Completed",
    },
    {
        "patient_id": "PAT-005",
        "first_name": "Sophia",
        "last_name": "Martinez",
        "patient_name": "Sophia Martinez",
        "date_of_birth": date(1995, 6, 30),
        "age": 31,
        "gender": "Female",
        "phone": "+1-555-0105",
        "address": "654 Cedar Blvd, Springfield",
        "status": "Registered",
    },
    {
        "patient_id": "PAT-006",
        "first_name": "David",
        "last_name": "Kim",
        "patient_name": "David Kim",
        "date_of_birth": date(1988, 9, 14),
        "age": 38,
        "gender": "Male",
        "phone": "+1-555-0106",
        "address": "987 Birch Lane, Springfield",
        "status": "Registered",
    },
    {
        "patient_id": "PAT-007",
        "first_name": "Emily",
        "last_name": "Watson",
        "patient_name": "Emily Watson",
        "date_of_birth": date(1992, 3, 18),
        "age": 34,
        "gender": "Female",
        "phone": "+1-555-0107",
        "address": "150 Walnut Court, Springfield",
        "status": "Registered",
    },
    {
        "patient_id": "PAT-008",
        "first_name": "Alexander",
        "last_name": "Wright",
        "patient_name": "Alexander Wright",
        "date_of_birth": date(1983, 12, 2),
        "age": 42,
        "gender": "Male",
        "phone": "+1-555-0108",
        "address": "882 Cypress Drive, Springfield",
        "status": "Registered",
    },
]


def get_demo_appointments() -> Dict[str, Any]:
    """
    Generate initial seed appointments.
    All token fields (token_id, token_number) are initialized to None because tokens
    must not be mock demo data; they are dynamically fetched from PostgreSQL.
    """
    from backend.services.appointment.schemas.appointment_schemas import (
        AppointmentResponse,
        AppointmentStatus,
        CancellationDetails,
        OperationalTimestamps,
        StatusAuditRecord,
    )

    today = date.today()
    yesterday = today - timedelta(days=1)
    now = datetime.utcnow()

    appointments: Dict[str, AppointmentResponse] = {}

    # 1. Scheduled appointment (APT-001)
    apt1_id = "APT-001"
    appointments[apt1_id] = AppointmentResponse(
        appointment_id=apt1_id,
        patient_id="PAT-001",
        patient_name="James Wilson",
        doctor_id="DOC-001",
        doctor_name="Dr. Sarah Smith",
        department_id="DEP-CARD",
        department_name="Cardiology",
        appointment_date=today,
        appointment_time="09:30 AM",
        status=AppointmentStatus.SCHEDULED,
        priority="Normal",
        token_id=None,
        token_number=None,
        notes="Routine annual cardiac checkup",
        timestamps=OperationalTimestamps(
            created_at=now - timedelta(hours=3),
            updated_at=now - timedelta(hours=3),
        ),
        history=[
            StatusAuditRecord(
                history_id=f"AUD-{apt1_id}-1",
                appointment_id=apt1_id,
                from_status=None,
                to_status=AppointmentStatus.SCHEDULED,
                changed_at=now - timedelta(hours=3),
                changed_by="Frontdesk Staff",
                notes="Appointment booked online",
            )
        ],
    )

    # 2. Checked-In appointment (APT-002) - Token unconfigured (None until fetched from PostgreSQL)
    apt2_id = "APT-002"
    check_in_time2 = now - timedelta(minutes=25)
    appointments[apt2_id] = AppointmentResponse(
        appointment_id=apt2_id,
        patient_id="PAT-002",
        patient_name="Michael Chen",
        doctor_id="DOC-001",
        doctor_name="Dr. Sarah Smith",
        department_id="DEP-CARD",
        department_name="Cardiology",
        appointment_date=today,
        appointment_time="10:00 AM",
        status=AppointmentStatus.CHECKED_IN,
        priority="Normal",
        token_id=None,
        token_number=None,
        notes="Follow-up on ECG report",
        timestamps=OperationalTimestamps(
            created_at=now - timedelta(hours=4),
            updated_at=check_in_time2,
            check_in_time=check_in_time2,
            queue_entry_time=check_in_time2,
        ),
        history=[
            StatusAuditRecord(
                history_id=f"AUD-{apt2_id}-1",
                appointment_id=apt2_id,
                from_status=None,
                to_status=AppointmentStatus.SCHEDULED,
                changed_at=now - timedelta(hours=4),
                changed_by="Receptionist Mary",
                notes="Booked at front counter",
            ),
            StatusAuditRecord(
                history_id=f"AUD-{apt2_id}-2",
                appointment_id=apt2_id,
                from_status=AppointmentStatus.SCHEDULED,
                to_status=AppointmentStatus.CHECKED_IN,
                changed_at=check_in_time2,
                changed_by="Kiosk Check-In",
                notes="Patient verified insurance & checked in",
            ),
        ],
    )

    # 3. In-Consultation appointment (APT-003) - Token unconfigured (None until fetched from PostgreSQL)
    apt3_id = "APT-003"
    check_in_time3 = now - timedelta(minutes=45)
    start_time3 = now - timedelta(minutes=15)
    appointments[apt3_id] = AppointmentResponse(
        appointment_id=apt3_id,
        patient_id="PAT-003",
        patient_name="Elena Rodriguez",
        doctor_id="DOC-002",
        doctor_name="Dr. Marcus Johnson",
        department_id="DEP-ORTHO",
        department_name="Orthopedics",
        appointment_date=today,
        appointment_time="10:15 AM",
        status=AppointmentStatus.IN_CONSULTATION,
        priority="Emergency",
        token_id=None,
        token_number=None,
        notes="Acute ankle trauma with suspected fracture",
        timestamps=OperationalTimestamps(
            created_at=now - timedelta(hours=2),
            updated_at=start_time3,
            check_in_time=check_in_time3,
            queue_entry_time=check_in_time3,
            consultation_start_time=start_time3,
        ),
        history=[
            StatusAuditRecord(
                history_id=f"AUD-{apt3_id}-1",
                appointment_id=apt3_id,
                from_status=None,
                to_status=AppointmentStatus.SCHEDULED,
                changed_at=now - timedelta(hours=2),
                changed_by="Triage Staff",
                notes="Emergency slot booked",
            ),
            StatusAuditRecord(
                history_id=f"AUD-{apt3_id}-2",
                appointment_id=apt3_id,
                from_status=AppointmentStatus.SCHEDULED,
                to_status=AppointmentStatus.CHECKED_IN,
                changed_at=check_in_time3,
                changed_by="Triage Staff",
                notes="Emergency priority escalated",
            ),
            StatusAuditRecord(
                history_id=f"AUD-{apt3_id}-3",
                appointment_id=apt3_id,
                from_status=AppointmentStatus.CHECKED_IN,
                to_status=AppointmentStatus.IN_CONSULTATION,
                changed_at=start_time3,
                changed_by="Dr. Marcus Johnson",
                notes="Called into exam room 2",
            ),
        ],
    )

    # 4. Completed appointment (APT-004) - Token unconfigured (None until fetched from PostgreSQL)
    apt4_id = "APT-004"
    check_in_time4 = now - timedelta(hours=2)
    start_time4 = now - timedelta(hours=1, minutes=40)
    end_time4 = now - timedelta(hours=1, minutes=10)
    appointments[apt4_id] = AppointmentResponse(
        appointment_id=apt4_id,
        patient_id="PAT-004",
        patient_name="Robert Taylor",
        doctor_id="DOC-003",
        doctor_name="Dr. Emily Davis",
        department_id="DEP-GEN",
        department_name="General Medicine",
        appointment_date=today,
        appointment_time="08:45 AM",
        status=AppointmentStatus.COMPLETED,
        priority="Normal",
        token_id=None,
        token_number=None,
        notes="Prescription renewal and lab review",
        timestamps=OperationalTimestamps(
            created_at=now - timedelta(days=1),
            updated_at=end_time4,
            check_in_time=check_in_time4,
            queue_entry_time=check_in_time4,
            consultation_start_time=start_time4,
            consultation_end_time=end_time4,
        ),
        history=[
            StatusAuditRecord(
                history_id=f"AUD-{apt4_id}-1",
                appointment_id=apt4_id,
                from_status=None,
                to_status=AppointmentStatus.SCHEDULED,
                changed_at=now - timedelta(days=1),
                changed_by="Online Portal",
                notes="Self-scheduled",
            ),
            StatusAuditRecord(
                history_id=f"AUD-{apt4_id}-2",
                appointment_id=apt4_id,
                from_status=AppointmentStatus.SCHEDULED,
                to_status=AppointmentStatus.CHECKED_IN,
                changed_at=check_in_time4,
                changed_by="Receptionist Mary",
                notes="Checked in on time",
            ),
            StatusAuditRecord(
                history_id=f"AUD-{apt4_id}-3",
                appointment_id=apt4_id,
                from_status=AppointmentStatus.CHECKED_IN,
                to_status=AppointmentStatus.IN_CONSULTATION,
                changed_at=start_time4,
                changed_by="Dr. Emily Davis",
                notes="Consultation commenced",
            ),
            StatusAuditRecord(
                history_id=f"AUD-{apt4_id}-4",
                appointment_id=apt4_id,
                from_status=AppointmentStatus.IN_CONSULTATION,
                to_status=AppointmentStatus.COMPLETED,
                changed_at=end_time4,
                changed_by="Dr. Emily Davis",
                notes="Prescription dispensed, discharge completed",
            ),
        ],
    )

    # 5. Cancelled appointment (APT-005)
    apt5_id = "APT-005"
    appointments[apt5_id] = AppointmentResponse(
        appointment_id=apt5_id,
        patient_id="PAT-005",
        patient_name="Sophia Martinez",
        doctor_id="DOC-004",
        doctor_name="Dr. Michael Brown",
        department_id="DEP-PED",
        department_name="Pediatrics",
        appointment_date=today,
        appointment_time="11:30 AM",
        status=AppointmentStatus.CANCELLED,
        priority="Normal",
        token_id=None,
        token_number=None,
        notes="Child feeling better, requested cancellation",
        timestamps=OperationalTimestamps(
            created_at=now - timedelta(hours=6),
            updated_at=now - timedelta(hours=1),
            cancelled_at=now - timedelta(hours=1),
        ),
        cancellation_details=CancellationDetails(
            reason="Patient Request",
            cancelled_at=now - timedelta(hours=1),
            cancelled_by="STF-001",
            notes="Parent called to cancel due to resolved symptoms",
        ),
        history=[
            StatusAuditRecord(
                history_id=f"AUD-{apt5_id}-1",
                appointment_id=apt5_id,
                from_status=None,
                to_status=AppointmentStatus.SCHEDULED,
                changed_at=now - timedelta(hours=6),
                changed_by="Parent",
                notes="Booked by phone",
            ),
            StatusAuditRecord(
                history_id=f"AUD-{apt5_id}-2",
                appointment_id=apt5_id,
                from_status=AppointmentStatus.SCHEDULED,
                to_status=AppointmentStatus.CANCELLED,
                changed_at=now - timedelta(hours=1),
                changed_by="STF-001",
                notes="Parent called to cancel due to resolved symptoms",
            ),
        ],
    )

    # 6. No-Show appointment (APT-006)
    apt6_id = "APT-006"
    appointments[apt6_id] = AppointmentResponse(
        appointment_id=apt6_id,
        patient_id="PAT-006",
        patient_name="David Kim",
        doctor_id="DOC-005",
        doctor_name="Dr. Priya Patel",
        department_id="DEP-DERM",
        department_name="Dermatology",
        appointment_date=yesterday,
        appointment_time="03:00 PM",
        status=AppointmentStatus.NO_SHOW,
        priority="Normal",
        token_id=None,
        token_number=None,
        notes="Skin allergy consultation",
        timestamps=OperationalTimestamps(
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=1),
        ),
        history=[
            StatusAuditRecord(
                history_id=f"AUD-{apt6_id}-1",
                appointment_id=apt6_id,
                from_status=None,
                to_status=AppointmentStatus.SCHEDULED,
                changed_at=now - timedelta(days=2),
                changed_by="Online Portal",
                notes="Booked online",
            ),
            StatusAuditRecord(
                history_id=f"AUD-{apt6_id}-2",
                appointment_id=apt6_id,
                from_status=AppointmentStatus.SCHEDULED,
                to_status=AppointmentStatus.NO_SHOW,
                changed_at=now - timedelta(days=1),
                changed_by="Staff System",
                notes="Patient failed to arrive 30 mins after scheduled slot",
            ),
        ],
    )

    return appointments


def get_demo_released_slots() -> Dict[str, Any]:
    """
    Generate released slots for cancelled demo appointments.
    """
    from backend.services.appointment.schemas.appointment_schemas import (
        SlotInventoryItem,
        SlotStatus,
    )

    today = date.today()
    key = f"DOC-004:{today}:11:30 AM"
    return {
        key: SlotInventoryItem(
            doctor_id="DOC-004",
            appointment_date=today,
            slot_time="11:30 AM",
            status=SlotStatus.RELEASED,
            appointment_id="APT-005",
            patient_name="Sophia Martinez",
        )
    }
