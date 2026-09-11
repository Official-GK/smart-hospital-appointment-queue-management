import uuid
from datetime import date, datetime
from typing import List, Optional
from fastapi import HTTPException

from backend.services.patient.models.patient_models import PatientRepository
from backend.services.patient.schemas.patient_schemas import (
    EligibleCheckInItem,
    PatientCheckInRequest,
    PatientCheckInResponse,
    PatientCreate,
    PatientResponse,
    PatientStatus,
)
from backend.services.appointment.services.appointment_service import appointment_service_instance
from backend.services.appointment.schemas.appointment_schemas import (
    AppointmentStatus,
    StatusTransitionRequest,
    AppointmentCreate,
)
from backend.services.queue.services.queue_service import queue_service_instance
from backend.services.queue.schemas.queue_schemas import QueuePriority, QueueStatus
from backend.database.demo_data import DEPARTMENTS, DOCTORS


class PatientService:
    """
    Patient domain service handling patient records, arrival tracking, and check-in workflows.
    """

    def __init__(self, repo: Optional[PatientRepository] = None):
        self.repo = repo or PatientRepository()
        self.appointment_service = appointment_service_instance
        self.queue_service = queue_service_instance

    def reset(self):
        self.repo.reset()

    def get_all_patients(self) -> List[PatientResponse]:
        return self.repo.get_all()

    def get_patient_by_id(self, patient_id: str) -> PatientResponse:
        patient = self.repo.get_by_id(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")
        return patient

    def search_patients(self, query: str) -> List[PatientResponse]:
        return self.repo.search(query)

    def create_patient(self, payload: PatientCreate) -> PatientResponse:
        # Check duplicate phone
        existing = self.repo.get_by_phone(payload.phone)
        if existing:
            raise HTTPException(status_code=409, detail=f"Patient with phone '{payload.phone}' already exists: {existing.patient_id}")
        return self.repo.create(payload)

    def get_eligible_check_ins(self) -> List[EligibleCheckInItem]:
        """
        Retrieves scheduled appointments awaiting physical check-in.
        """
        scheduled_apts = self.appointment_service.get_appointments(status=AppointmentStatus.SCHEDULED)
        
        items: List[EligibleCheckInItem] = []
        for apt in scheduled_apts:
            patient = self.repo.get_by_id(apt.patient_id)
            phone = patient.phone if patient else None

            items.append(
                EligibleCheckInItem(
                    appointment_id=apt.appointment_id,
                    patient_id=apt.patient_id,
                    patient_name=apt.patient_name,
                    phone=phone,
                    appointment_date=apt.appointment_date,
                    appointment_time=apt.appointment_time,
                    doctor_id=apt.doctor_id,
                    doctor_name=apt.doctor_name,
                    department_id=apt.department_id,
                    department_name=apt.department_name,
                    priority=apt.priority,
                    is_walk_in=apt.is_walk_in,
                    status=apt.status.value,
                    can_check_in=True,
                )
            )
        return items

    def check_in_patient(self, request: PatientCheckInRequest) -> PatientCheckInResponse:
        """
        Executes check-in for an arriving patient (either scheduled appointment or walk-in visit).
        - Records physical arrival timestamp
        - Transitions status to Checked-In
        - Automatically places patient into active queue with assigned token
        - Calculates queue position and estimated wait time
        """
        arrival_time = request.arrival_time or datetime.utcnow()
        check_in_id = f"CHK-{uuid.uuid4().hex[:8].upper()}"

        # -------------------------------------------------------------
        # 1. Resolve / Ensure Patient Demographic Record
        # -------------------------------------------------------------
        patient: Optional[PatientResponse] = None
        if request.patient_id:
            patient = self.repo.get_by_id(request.patient_id)

        if not patient and request.phone:
            patient = self.repo.get_by_phone(request.phone)

        if not patient:
            # Auto-register walk-in / new patient
            full_name = (request.patient_name or "Walk-in Patient").strip()
            parts = full_name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else "Patient"
            phone = request.phone.strip() if request.phone else f"+1-555-{uuid.uuid4().hex[:4]}"
            patient = self.repo.create(
                PatientCreate(
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    gender="Other",
                    address="Walk-in Registration",
                )
            )

        # -------------------------------------------------------------
        # 2. Case A: Check-In for an Existing Appointment
        # -------------------------------------------------------------
        if request.appointment_id and not request.is_walk_in:
            apt = self.appointment_service.get_appointment_by_id(request.appointment_id)
            if not apt:
                raise HTTPException(status_code=404, detail=f"Appointment '{request.appointment_id}' not found")

            if apt.status == AppointmentStatus.CHECKED_IN:
                raise HTTPException(status_code=400, detail=f"Appointment '{apt.appointment_id}' is already checked in")

            if apt.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot check in appointment with status '{apt.status.value}'",
                )

            # Transition status to Checked-In via appointment service
            # This sets check_in_time and queue_entry_time, and calls queue_service.add_to_queue(...)
            updated_apt = self.appointment_service.transition_status(
                appointment_id=apt.appointment_id,
                request=StatusTransitionRequest(
                    new_status=AppointmentStatus.CHECKED_IN,
                    changed_by=request.checked_in_by or "Front-Desk Staff",
                    notes=request.notes or f"Physical check-in at {arrival_time.strftime('%I:%M %p')}",
                ),
            )

            # Update patient model status & last arrival time
            self.repo.update_status(
                patient_id=patient.patient_id,
                status=PatientStatus.CHECKED_IN,
                arrival_time=arrival_time,
            )

            # Retrieve active queue to calculate position
            live_queue = self.queue_service.get_live_queue(
                doctor_id=updated_apt.doctor_id,
                department_id=updated_apt.department_id,
            )
            queue_pos = next(
                (idx + 1 for idx, q in enumerate(live_queue) if q.appointment_id == updated_apt.appointment_id),
                len(live_queue) or 1,
            )
            estimated_wait = next(
                (q.estimated_wait_minutes for q in live_queue if q.appointment_id == updated_apt.appointment_id),
                15,
            )

            return PatientCheckInResponse(
                check_in_id=check_in_id,
                patient_id=patient.patient_id,
                patient_name=updated_apt.patient_name,
                appointment_id=updated_apt.appointment_id,
                status="Checked-In",
                arrival_time=arrival_time,
                token_id=updated_apt.token_id,
                token_number=updated_apt.token_number,
                queue_position=queue_pos,
                estimated_wait_minutes=estimated_wait,
                doctor_id=updated_apt.doctor_id,
                doctor_name=updated_apt.doctor_name,
                department_id=updated_apt.department_id,
                department_name=updated_apt.department_name,
                priority=updated_apt.priority,
                is_walk_in=False,
                notes=request.notes,
            )

        # -------------------------------------------------------------
        # 3. Case B: Walk-In Patient Check-In
        # -------------------------------------------------------------
        # Resolve doctor and department
        doctor_id = request.doctor_id or "DOC-001"
        doc_info = next((d for d in DOCTORS if d["doctor_id"] == doctor_id), None)
        doctor_name = request.doctor_name or (doc_info["doctor_name"] if doc_info else "Attending Physician")
        department_id = request.department_id or (doc_info["department_id"] if doc_info else "DEP-GEN")
        dept_info = next((dep for dep in DEPARTMENTS if dep["department_id"] == department_id), None)
        department_name = request.department_name or (dept_info["department_name"] if dept_info else "General Medicine")

        priority_val = request.priority.title() if request.priority else "Normal"
        queue_priority = QueuePriority.EMERGENCY if priority_val.lower() == "emergency" else QueuePriority.NORMAL

        walk_in_apt_id = f"WLK-{uuid.uuid4().hex[:6].upper()}"

        # Directly add to active queue
        queue_token = self.queue_service.add_to_queue(
            appointment_id=walk_in_apt_id,
            patient_id=patient.patient_id,
            patient_name=patient.patient_name,
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            department_id=department_id,
            department_name=department_name,
            priority=queue_priority,
            is_walk_in=True,
        )

        # Update patient model status & last arrival time
        self.repo.update_status(
            patient_id=patient.patient_id,
            status=PatientStatus.CHECKED_IN,
            arrival_time=arrival_time,
        )

        # Retrieve queue position
        live_queue = self.queue_service.get_live_queue(doctor_id=doctor_id, department_id=department_id)
        queue_pos = next(
            (idx + 1 for idx, q in enumerate(live_queue) if q.appointment_id == walk_in_apt_id),
            1,
        )

        return PatientCheckInResponse(
            check_in_id=check_in_id,
            patient_id=patient.patient_id,
            patient_name=patient.patient_name,
            appointment_id=walk_in_apt_id,
            status="Checked-In",
            arrival_time=arrival_time,
            token_id=queue_token.token_id,
            token_number=queue_token.token_number,
            queue_position=queue_pos,
            estimated_wait_minutes=queue_token.estimated_wait_minutes,
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            department_id=department_id,
            department_name=department_name,
            priority=priority_val,
            is_walk_in=True,
            notes=request.notes or "Walk-in check-in",
        )


patient_service_instance = PatientService()
