from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from backend.services.appointment.schemas.appointment_schemas import (
    AppointmentResponse,
    AppointmentStatus,
    CancellationDetails,
    OperationalTimestamps,
    SlotInventoryItem,
    SlotStatus,
    StatusAuditRecord,
)

DEPARTMENTS = [
    {"department_id": "DEP-CARD", "department_name": "Cardiology"},
    {"department_id": "DEP-ORTHO", "department_name": "Orthopedics"},
    {"department_id": "DEP-GEN", "department_name": "General Medicine"},
    {"department_id": "DEP-PED", "department_name": "Pediatrics"},
    {"department_id": "DEP-DERM", "department_name": "Dermatology"},
]

DOCTORS = [
    {"doctor_id": "DOC-001", "doctor_name": "Dr. Sarah Smith", "department_id": "DEP-CARD", "department_name": "Cardiology"},
    {"doctor_id": "DOC-002", "doctor_name": "Dr. Marcus Johnson", "department_id": "DEP-ORTHO", "department_name": "Orthopedics"},
    {"doctor_id": "DOC-003", "doctor_name": "Dr. Emily Davis", "department_id": "DEP-GEN", "department_name": "General Medicine"},
    {"doctor_id": "DOC-004", "doctor_name": "Dr. Michael Brown", "department_id": "DEP-PED", "department_name": "Pediatrics"},
    {"doctor_id": "DOC-005", "doctor_name": "Dr. Priya Patel", "department_id": "DEP-DERM", "department_name": "Dermatology"},
]

DEFAULT_SLOTS = [
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


class AppointmentRepository:
    def __init__(self):
        self._appointments: Dict[str, AppointmentResponse] = {}
        self._released_slots: Dict[str, SlotInventoryItem] = {}
        self._seed_appointments()

    def reset(self):
        self._appointments.clear()
        self._released_slots.clear()
        self._seed_appointments()

    def _seed_appointments(self):
        today = date.today()
        yesterday = today - timedelta(days=1)
        now = datetime.utcnow()

        # 1. Scheduled appointment
        apt1_id = "APT-001"
        self._appointments[apt1_id] = AppointmentResponse(
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

        # 2. Checked-In appointment (In live queue)
        apt2_id = "APT-002"
        check_in_time2 = now - timedelta(minutes=25)
        self._appointments[apt2_id] = AppointmentResponse(
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
            token_number="A-101",
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

        # 3. In-Consultation appointment (Emergency)
        apt3_id = "APT-003"
        check_in_time3 = now - timedelta(minutes=45)
        start_time3 = now - timedelta(minutes=15)
        self._appointments[apt3_id] = AppointmentResponse(
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
            token_number="A-102",
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

        # 4. Completed appointment
        apt4_id = "APT-004"
        check_in_time4 = now - timedelta(hours=2)
        start_time4 = now - timedelta(hours=1, minutes=40)
        end_time4 = now - timedelta(hours=1, minutes=10)
        self._appointments[apt4_id] = AppointmentResponse(
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
            token_number="A-099",
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

        # 5. Cancelled appointment
        apt5_id = "APT-005"
        self._appointments[apt5_id] = AppointmentResponse(
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
        self.release_slot(
            doctor_id="DOC-004",
            appointment_date=today,
            slot_time="11:30 AM",
            appointment_id=apt5_id,
            patient_name="Sophia Martinez",
        )

        # 6. No-Show appointment
        apt6_id = "APT-006"
        self._appointments[apt6_id] = AppointmentResponse(
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

    def get_all(self) -> List[AppointmentResponse]:
        return list(self._appointments.values())

    def get_by_id(self, appointment_id: str) -> Optional[AppointmentResponse]:
        return self._appointments.get(appointment_id)

    def get_next_appointment_id(self) -> str:
        import re
        numbers = []
        for aid in self._appointments.keys():
            match = re.search(r"\d+", aid)
            if match:
                numbers.append(int(match.group()))
        next_num = max(numbers, default=0) + 1
        return f"APT-{next_num:03d}"

    def get_next_patient_id(self) -> str:
        import re
        numbers = []
        for apt in self._appointments.values():
            if apt.patient_id:
                match = re.search(r"\d+", apt.patient_id)
                if match:
                    numbers.append(int(match.group()))
        next_num = max(numbers, default=0) + 1
        return f"PAT-{next_num:03d}"

    def save(self, appointment: AppointmentResponse) -> AppointmentResponse:
        self._appointments[appointment.appointment_id] = appointment
        return appointment

    def release_slot(
        self,
        doctor_id: str,
        appointment_date: date,
        slot_time: str,
        appointment_id: str,
        patient_name: Optional[str] = None,
    ) -> SlotInventoryItem:
        key = f"{doctor_id}:{appointment_date}:{slot_time}"
        item = SlotInventoryItem(
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            slot_time=slot_time,
            status=SlotStatus.RELEASED,
            appointment_id=appointment_id,
            patient_name=patient_name,
        )
        self._released_slots[key] = item
        return item

    def get_slots(
        self,
        doctor_id: Optional[str] = None,
        appointment_date: Optional[date] = None,
    ) -> List[SlotInventoryItem]:
        target_date = appointment_date or date.today()
        doctors_to_query = [d["doctor_id"] for d in DOCTORS] if not doctor_id else [doctor_id]

        items: List[SlotInventoryItem] = []
        for doc in doctors_to_query:
            apts = [
                a for a in self._appointments.values()
                if a.doctor_id == doc and a.appointment_date == target_date
            ]
            apt_by_time = {a.appointment_time: a for a in apts}
            all_times = list(dict.fromkeys(DEFAULT_SLOTS + list(apt_by_time.keys())))

            for t in all_times:
                if t in apt_by_time:
                    apt = apt_by_time[t]
                    if apt.status == AppointmentStatus.CANCELLED:
                        items.append(
                            SlotInventoryItem(
                                doctor_id=doc,
                                appointment_date=target_date,
                                slot_time=t,
                                status=SlotStatus.RELEASED,
                                appointment_id=apt.appointment_id,
                                patient_name=apt.patient_name,
                            )
                        )
                    else:
                        items.append(
                            SlotInventoryItem(
                                doctor_id=doc,
                                appointment_date=target_date,
                                slot_time=t,
                                status=SlotStatus.BOOKED,
                                appointment_id=apt.appointment_id,
                                patient_name=apt.patient_name,
                            )
                        )
                else:
                    key = f"{doc}:{target_date}:{t}"
                    if key in self._released_slots:
                        items.append(self._released_slots[key])
                    else:
                        items.append(
                            SlotInventoryItem(
                                doctor_id=doc,
                                appointment_date=target_date,
                                slot_time=t,
                                status=SlotStatus.AVAILABLE,
                                appointment_id=None,
                                patient_name=None,
                            )
                        )
        return items

    def is_slot_available(
        self,
        doctor_id: str,
        appointment_date: date,
        slot_time: str,
        exclude_appointment_id: Optional[str] = None,
    ) -> bool:
        for apt in self._appointments.values():
            if (
                apt.doctor_id == doctor_id
                and apt.appointment_date == appointment_date
                and apt.appointment_time == slot_time
                and apt.status not in (AppointmentStatus.CANCELLED,)
                and (exclude_appointment_id is None or apt.appointment_id != exclude_appointment_id)
            ):
                return False
        return True

    def book_slot(
        self,
        doctor_id: str,
        appointment_date: date,
        slot_time: str,
        appointment_id: str,
        patient_name: Optional[str] = None,
    ):
        key = f"{doctor_id}:{appointment_date}:{slot_time}"
        if key in self._released_slots:
            del self._released_slots[key]

    def get_released_slots_count(self) -> int:
        return sum(1 for a in self._appointments.values() if a.status == AppointmentStatus.CANCELLED)


appointment_repo = AppointmentRepository()

