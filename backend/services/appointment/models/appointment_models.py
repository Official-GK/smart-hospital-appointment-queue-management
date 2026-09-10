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

from backend.database.demo_data import (
    DEFAULT_SLOTS,
    DEPARTMENTS,
    DOCTORS,
    get_demo_appointments,
    get_demo_released_slots,
)


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
        self._appointments = get_demo_appointments()
        self._released_slots = get_demo_released_slots()

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
            doctor_info = next((d for d in DOCTORS if d["doctor_id"] == doc), None)
            gap = 30
            if doctor_info:
                dept_info = next((dep for dep in DEPARTMENTS if dep["department_id"] == doctor_info["department_id"]), None)
                if dept_info and "avg_consultation_time" in dept_info:
                    gap = int(dept_info["avg_consultation_time"])

            # Generate slots from 09:00 AM to 05:00 PM based on gap
            start_time = datetime.strptime("09:00 AM", "%I:%M %p")
            end_time = datetime.strptime("05:00 PM", "%I:%M %p")
            generated_slots = []
            curr = start_time
            while curr < end_time:
                # Remove leading zero for hours? No, DEFAULT_SLOTS has leading zero (e.g. 09:00 AM)
                generated_slots.append(curr.strftime("%I:%M %p"))
                curr += timedelta(minutes=gap)

            apts = [
                a for a in self._appointments.values()
                if a.doctor_id == doc and a.appointment_date == target_date
            ]
            apt_by_time = {a.appointment_time: a for a in apts}
            all_times = list(dict.fromkeys(generated_slots + list(apt_by_time.keys())))

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

