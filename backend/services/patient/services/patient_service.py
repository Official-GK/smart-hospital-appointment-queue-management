import uuid
from datetime import date, datetime
from typing import List, Optional, Tuple
from fastapi import HTTPException

from backend.services.patient.models.patient_models import PatientRepository
from backend.services.patient.schemas.patient_schemas import (
    EligibleCheckInItem,
    PatientCheckInRequest,
    PatientCheckInResponse,
    PatientCreate,
    PatientResponse,
    PatientStatus,
    PatientAuditRecord,
    PatientUpdateRequest,
    TokenHistoryItem,
    VisitHistoryItem,
    PatientProfileResponse,
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

    @staticmethod
    def _calculate_age(dob: Optional[date]) -> Optional[int]:
        if not dob:
            return None
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    @staticmethod
    def _mask_contact_info(phone: str, address: Optional[str]) -> Tuple[str, Optional[str]]:
        clean_phone = phone.strip()
        if len(clean_phone) >= 7:
            prefix = clean_phone[:4]
            suffix = clean_phone[-4:]
            masked_phone = f"{prefix}***-**{suffix}"
        else:
            masked_phone = "***-***-****"

        masked_address = None
        if address:
            parts = address.split(",", 1)
            if len(parts) > 1:
                masked_address = f"*** {parts[0].split()[-1] if parts[0].split() else 'Street'}, {parts[1].strip()}"
            else:
                masked_address = "*** Confidential Address"

        return masked_phone, masked_address

    def get_patient_profile(
        self,
        patient_id: str,
        role: str = "Staff",
        mask_sensitive: bool = False,
    ) -> PatientProfileResponse:
        patient = self.get_patient_by_id(patient_id)
        age = self._calculate_age(patient.date_of_birth)

        authorized_roles = {"administrator", "doctor", "staff", "receptionist", "nurse", "management"}
        should_mask = mask_sensitive or (role.lower() not in authorized_roles)

        disp_phone = patient.phone
        disp_address = patient.address
        if should_mask:
            disp_phone, disp_address = self._mask_contact_info(patient.phone, patient.address)

        all_apts = [a for a in self.appointment_service.repo.get_all() if a.patient_id == patient_id]

        active_statuses = {
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CHECKED_IN,
            AppointmentStatus.IN_CONSULTATION,
        }

        active_appointments: List[VisitHistoryItem] = []
        visit_history: List[VisitHistoryItem] = []
        token_history: List[TokenHistoryItem] = []

        for apt in sorted(all_apts, key=lambda x: (x.appointment_date, x.appointment_time), reverse=True):
            item = VisitHistoryItem(
                appointment_id=apt.appointment_id,
                appointment_date=apt.appointment_date,
                appointment_time=apt.appointment_time,
                doctor_id=apt.doctor_id,
                doctor_name=apt.doctor_name,
                department_id=apt.department_id,
                department_name=apt.department_name,
                status=apt.status.value,
                priority=apt.priority,
                is_walk_in=apt.is_walk_in,
                booking_time=apt.timestamps.created_at,
                check_in_time=apt.timestamps.check_in_time,
                queue_entry_time=apt.timestamps.queue_entry_time,
                consultation_start_time=apt.timestamps.consultation_start_time,
                completion_time=apt.timestamps.consultation_end_time,
                notes=apt.notes,
            )

            if apt.status in active_statuses:
                active_appointments.append(item)
            else:
                visit_history.append(item)

            if apt.token_number:
                token_history.append(
                    TokenHistoryItem(
                        token_id=apt.token_id or f"TOK-{apt.token_number}",
                        token_number=apt.token_number,
                        appointment_id=apt.appointment_id,
                        doctor_id=apt.doctor_id,
                        doctor_name=apt.doctor_name,
                        department_id=apt.department_id,
                        department_name=apt.department_name,
                        priority=apt.priority,
                        status=apt.status.value,
                        created_at=apt.timestamps.queue_entry_time or apt.timestamps.booking_time,
                    )
                )

        audit_trail = self.repo.get_audit_trail(patient_id)

        return PatientProfileResponse(
            patient_id=patient.patient_id,
            first_name=patient.first_name,
            last_name=patient.last_name,
            patient_name=patient.patient_name,
            date_of_birth=patient.date_of_birth,
            age=age,
            gender=patient.gender,
            phone=disp_phone,
            address=disp_address,
            status=patient.status,
            created_at=patient.created_at,
            last_arrival_time=patient.last_arrival_time,
            is_masked=should_mask,
            active_appointments=active_appointments,
            visit_history=visit_history,
            token_history=token_history,
            audit_trail=audit_trail,
        )

    def update_patient_details(
        self,
        patient_id: str,
        payload: PatientUpdateRequest,
    ) -> Tuple[PatientResponse, List[PatientAuditRecord]]:
        if payload.phone:
            existing = self.repo.get_by_phone(payload.phone)
            if existing and existing.patient_id != patient_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Phone number '{payload.phone}' is already registered to patient '{existing.patient_id}'",
                )

        updated_patient, audits = self.repo.update_patient(patient_id, payload)
        if not updated_patient:
            raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")
        return updated_patient, audits

    def get_patient_audit_trail(self, patient_id: str) -> List[PatientAuditRecord]:
        self.get_patient_by_id(patient_id)
        return self.repo.get_audit_trail(patient_id)


patient_service_instance = PatientService()
