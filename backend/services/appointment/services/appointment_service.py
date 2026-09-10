from datetime import date, datetime
from typing import Dict, List, Optional
from fastapi import HTTPException
from backend.services.appointment.models.appointment_models import DEPARTMENTS, DOCTORS, appointment_repo
from backend.services.appointment.schemas.appointment_schemas import (
    AppointmentCancelRequest,
    AppointmentCreate,
    AppointmentRescheduleRequest,
    AppointmentResponse,
    AppointmentStatistics,
    AppointmentStatus,
    CancellationDetails,
    OperationalTimestamps,
    SlotInventoryItem,
    StatusAuditRecord,
    StatusTransitionRequest,
)
from backend.database.token_fetcher import (
    fetch_token_by_appointment,
    fetch_tokens_by_appointments,
    save_token,
)
from backend.services.queue.schemas.queue_schemas import QueuePriority, QueueStatus
from backend.services.queue.services.queue_service import queue_service_instance

VALID_TRANSITIONS = {
    AppointmentStatus.SCHEDULED: {
        AppointmentStatus.CHECKED_IN,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    },
    AppointmentStatus.CHECKED_IN: {
        AppointmentStatus.IN_CONSULTATION,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    },
    AppointmentStatus.IN_CONSULTATION: {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.COMPLETED: set(),
    AppointmentStatus.CANCELLED: set(),
    AppointmentStatus.NO_SHOW: set(),
}


class AppointmentService:
    def __init__(self):
        self.repo = appointment_repo
        self.queue_service = queue_service_instance

    def get_appointments(
        self,
        status: Optional[AppointmentStatus] = None,
        department_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        appointment_date: Optional[date] = None,
    ) -> List[AppointmentResponse]:
        appointments = self.repo.get_all()

        if status:
            appointments = [a for a in appointments if a.status == status]
        if department_id:
            appointments = [a for a in appointments if a.department_id == department_id]
        if doctor_id:
            appointments = [a for a in appointments if a.doctor_id == doctor_id]
        if appointment_date:
            appointments = [a for a in appointments if a.appointment_date == appointment_date]

        # Sort by appointment_date and appointment_time descending
        appointments.sort(key=lambda a: (a.appointment_date, a.appointment_time), reverse=True)

        # Fetch tokens dynamically from PostgreSQL database (handled gracefully with try...except)
        try:
            apt_ids = [a.appointment_id for a in appointments]
            db_tokens = fetch_tokens_by_appointments(apt_ids)
            if db_tokens:
                for a in appointments:
                    db_tok = db_tokens.get(a.appointment_id)
                    if db_tok:
                        a.token_id = db_tok.get("token_id") or a.token_id
                        a.token_number = db_tok.get("token_number") or a.token_number
        except Exception:
            # PostgreSQL fetch error handled gracefully
            pass

        return appointments

    def get_appointment_by_id(self, appointment_id: str) -> AppointmentResponse:
        apt = self.repo.get_by_id(appointment_id)
        if not apt:
            raise HTTPException(status_code=404, detail=f"Appointment with ID '{appointment_id}' not found")

        # Fetch token dynamically from PostgreSQL database (handled gracefully with try...except)
        try:
            db_tok = fetch_token_by_appointment(appointment_id)
            if db_tok:
                apt.token_id = db_tok.get("token_id") or apt.token_id
                apt.token_number = db_tok.get("token_number") or apt.token_number
        except Exception:
            # PostgreSQL fetch error handled gracefully
            pass

        return apt

    def get_appointment_history(self, appointment_id: str) -> List[StatusAuditRecord]:
        apt = self.get_appointment_by_id(appointment_id)
        return apt.history

    def create_appointment(self, payload: AppointmentCreate) -> AppointmentResponse:
        # Validate patient name
        if not payload.patient_name or not payload.patient_name.strip():
            raise HTTPException(status_code=400, detail="Patient name is required.")

        # Validate doctor
        doctor = next((d for d in DOCTORS if d["doctor_id"] == payload.doctor_id), None)
        if not doctor:
            raise HTTPException(status_code=400, detail=f"Invalid doctor_id '{payload.doctor_id}'")

        # Validate department
        department = next((dep for dep in DEPARTMENTS if dep["department_id"] == payload.department_id), None)
        if not department:
            department = next((dep for dep in DEPARTMENTS if dep["department_id"] == doctor["department_id"]), None)
            if not department:
                raise HTTPException(status_code=400, detail=f"Invalid department_id '{payload.department_id}'")

        # Validate time slot
        if not payload.appointment_time or not payload.appointment_time.strip():
            raise HTTPException(status_code=400, detail="Appointment time slot is required.")

        # Prevent double-booking / overbooking
        if not self.repo.is_slot_available(payload.doctor_id, payload.appointment_date, payload.appointment_time):
            raise HTTPException(
                status_code=400,
                detail=f"Time slot '{payload.appointment_time}' on {payload.appointment_date} for {doctor['doctor_name']} is already booked.",
            )

        # Generate unique IDs
        apt_id = self.repo.get_next_appointment_id()
        patient_id = payload.patient_id.strip() if (payload.patient_id and payload.patient_id.strip()) else self.repo.get_next_patient_id()
        staff_id = payload.staff_id.strip() if (payload.staff_id and payload.staff_id.strip()) else "Staff Member"
        now = datetime.utcnow()

        new_appointment = AppointmentResponse(
            appointment_id=apt_id,
            patient_id=patient_id,
            patient_name=payload.patient_name.strip(),
            doctor_id=payload.doctor_id,
            doctor_name=doctor["doctor_name"],
            department_id=department["department_id"],
            department_name=department["department_name"],
            appointment_date=payload.appointment_date,
            appointment_time=payload.appointment_time.strip(),
            status=AppointmentStatus.SCHEDULED,
            priority=payload.priority or "Normal",
            token_number=None,
            notes=payload.notes,
            timestamps=OperationalTimestamps(
                created_at=now,
                updated_at=now,
            ),
            history=[
                StatusAuditRecord(
                    history_id=f"AUD-{apt_id}-1",
                    appointment_id=apt_id,
                    from_status=None,
                    to_status=AppointmentStatus.SCHEDULED,
                    changed_at=now,
                    changed_by=staff_id,
                    notes=payload.notes or "Initial appointment booking",
                )
            ],
        )

        saved_apt = self.repo.save(new_appointment)
        self.repo.book_slot(
            doctor_id=payload.doctor_id,
            appointment_date=payload.appointment_date,
            slot_time=payload.appointment_time.strip(),
            appointment_id=apt_id,
            patient_name=payload.patient_name.strip(),
        )
        return saved_apt

    def cancel_appointment(self, appointment_id: str, request: AppointmentCancelRequest) -> AppointmentResponse:
        apt = self.get_appointment_by_id(appointment_id)

        if apt.status == AppointmentStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail="Cannot cancel an appointment that has already been completed.",
            )
        if apt.status == AppointmentStatus.CANCELLED:
            raise HTTPException(
                status_code=400,
                detail="Appointment is already cancelled.",
            )

        if not request.reason or not request.reason.strip():
            raise HTTPException(status_code=400, detail="Cancellation reason is required.")
        if not request.staff_id or not request.staff_id.strip():
            raise HTTPException(status_code=400, detail="Staff ID is required.")

        now = datetime.utcnow()
        current_status = apt.status

        # Update timestamps
        apt.timestamps.updated_at = now
        apt.timestamps.cancelled_at = now

        # Update cancellation details
        apt.cancellation_details = CancellationDetails(
            reason=request.reason.strip(),
            cancelled_at=now,
            cancelled_by=request.staff_id.strip(),
            notes=request.notes,
        )

        # Update live queue if present
        self.queue_service.update_queue_status(
            appointment_id=apt.appointment_id,
            status=QueueStatus.ABANDONED,
        )

        # Release booked slot immediately back to inventory
        self.repo.release_slot(
            doctor_id=apt.doctor_id,
            appointment_date=apt.appointment_date,
            slot_time=apt.appointment_time,
            appointment_id=apt.appointment_id,
            patient_name=apt.patient_name,
        )

        # Update status
        apt.status = AppointmentStatus.CANCELLED

        # Record audit history
        audit_entry = StatusAuditRecord(
            history_id=f"AUD-{apt.appointment_id}-{len(apt.history) + 1}",
            appointment_id=apt.appointment_id,
            from_status=current_status,
            to_status=AppointmentStatus.CANCELLED,
            changed_at=now,
            changed_by=request.staff_id.strip(),
            notes=f"Cancellation Reason: {request.reason.strip()}" + (f" - Notes: {request.notes}" if request.notes else ""),
        )
        apt.history.append(audit_entry)

        return self.repo.save(apt)

    def reschedule_appointment(
        self,
        appointment_id: str,
        request: AppointmentRescheduleRequest,
    ) -> AppointmentResponse:
        apt = self.get_appointment_by_id(appointment_id)

        if apt.status == AppointmentStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail="Cannot modify an appointment that has already been completed.",
            )
        if apt.status == AppointmentStatus.CANCELLED:
            raise HTTPException(
                status_code=400,
                detail="Cannot modify an appointment that has been cancelled.",
            )
        if apt.status == AppointmentStatus.IN_CONSULTATION:
            raise HTTPException(
                status_code=400,
                detail="Cannot modify an appointment that is currently in consultation.",
            )

        if not request.staff_id or not request.staff_id.strip():
            raise HTTPException(status_code=400, detail="Staff ID is required to modify an appointment.")

        target_doctor_id = request.doctor_id or apt.doctor_id
        target_date = request.appointment_date or apt.appointment_date
        target_time = request.appointment_time or apt.appointment_time

        doctor = next((d for d in DOCTORS if d["doctor_id"] == target_doctor_id), None)
        if not doctor:
            raise HTTPException(status_code=400, detail=f"Invalid doctor_id '{target_doctor_id}'.")

        department = next((dep for dep in DEPARTMENTS if dep["department_id"] == doctor["department_id"]), None)
        if not department:
            raise HTTPException(status_code=400, detail=f"Department not found for doctor '{target_doctor_id}'.")

        # Check if anything changed
        no_changes = (
            target_doctor_id == apt.doctor_id
            and target_date == apt.appointment_date
            and target_time == apt.appointment_time
        )
        if no_changes:
            return apt

        # Validate slot availability for new doctor, date, and time
        available = self.repo.is_slot_available(
            doctor_id=target_doctor_id,
            appointment_date=target_date,
            slot_time=target_time,
            exclude_appointment_id=apt.appointment_id,
        )
        if not available:
            raise HTTPException(
                status_code=400,
                detail=f"Time slot '{target_time}' on {target_date} for {doctor['doctor_name']} is already booked.",
            )

        # Capture old and new slot details
        old_slot = {
            "doctor_id": apt.doctor_id,
            "doctor_name": apt.doctor_name,
            "department_id": apt.department_id,
            "department_name": apt.department_name,
            "appointment_date": str(apt.appointment_date),
            "appointment_time": apt.appointment_time,
        }
        new_slot = {
            "doctor_id": target_doctor_id,
            "doctor_name": doctor["doctor_name"],
            "department_id": department["department_id"],
            "department_name": department["department_name"],
            "appointment_date": str(target_date),
            "appointment_time": target_time,
        }

        # Release old slot
        self.repo.release_slot(
            doctor_id=apt.doctor_id,
            appointment_date=apt.appointment_date,
            slot_time=apt.appointment_time,
            appointment_id=apt.appointment_id,
            patient_name=f"Rescheduled from {apt.appointment_id}",
        )

        # Book new slot
        self.repo.book_slot(
            doctor_id=target_doctor_id,
            appointment_date=target_date,
            slot_time=target_time,
            appointment_id=apt.appointment_id,
            patient_name=apt.patient_name,
        )

        now = datetime.utcnow()
        apt.timestamps.updated_at = now

        # Build audit log entry with staff ID, old slot details, and new slot details
        audit_notes = (
            f"Rescheduled: [{old_slot['doctor_name']} ({old_slot['department_name']}), {old_slot['appointment_date']} at {old_slot['appointment_time']}] "
            f"-> [{new_slot['doctor_name']} ({new_slot['department_name']}), {new_slot['appointment_date']} at {new_slot['appointment_time']}]. "
            f"Reason: {request.reason or 'Patient Request'}"
        )
        if request.notes:
            audit_notes += f" - Notes: {request.notes}"

        audit_entry = StatusAuditRecord(
            history_id=f"AUD-{apt.appointment_id}-{len(apt.history) + 1}",
            appointment_id=apt.appointment_id,
            from_status=apt.status,
            to_status=apt.status,
            changed_at=now,
            changed_by=request.staff_id.strip(),
            notes=audit_notes,
            old_slot_details=old_slot,
            new_slot_details=new_slot,
        )
        apt.history.append(audit_entry)

        # Update appointment details
        apt.doctor_id = target_doctor_id
        apt.doctor_name = doctor["doctor_name"]
        apt.department_id = department["department_id"]
        apt.department_name = department["department_name"]
        apt.appointment_date = target_date
        apt.appointment_time = target_time

        return self.repo.save(apt)

    def transition_status(self, appointment_id: str, request: StatusTransitionRequest) -> AppointmentResponse:
        apt = self.get_appointment_by_id(appointment_id)
        current_status = apt.status
        target_status = request.new_status

        if current_status == target_status:
            return apt

        allowed = VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition status from '{current_status.value}' to '{target_status.value}'. "
                f"Allowed target statuses: {[s.value for s in allowed]}",
            )

        now = datetime.utcnow()
        apt.timestamps.updated_at = now

        # Update Operational Timestamps and Queue State
        if target_status == AppointmentStatus.CHECKED_IN:
            apt.timestamps.check_in_time = now
            apt.timestamps.queue_entry_time = now
            priority = QueuePriority.EMERGENCY if apt.priority.lower() == "emergency" else QueuePriority.NORMAL
            queue_token = self.queue_service.add_to_queue(
                appointment_id=apt.appointment_id,
                patient_id=apt.patient_id,
                patient_name=apt.patient_name,
                doctor_id=apt.doctor_id,
                doctor_name=apt.doctor_name,
                department_id=apt.department_id,
                department_name=apt.department_name,
                priority=priority,
            )
            apt.token_id = queue_token.token_id
            apt.token_number = queue_token.token_number

            # Persist token to PostgreSQL (handled gracefully with try...except)
            try:
                save_token({
                    "token_id": queue_token.token_id,
                    "token_number": queue_token.token_number,
                    "appointment_id": apt.appointment_id,
                    "patient_id": apt.patient_id,
                    "patient_name": apt.patient_name,
                    "doctor_id": apt.doctor_id,
                    "doctor_name": apt.doctor_name,
                    "department_id": apt.department_id,
                    "department_name": apt.department_name,
                    "priority": priority.value,
                    "status": queue_token.status.value,
                    "created_at": queue_token.queue_entry_time,
                    "queue_entry_time": queue_token.queue_entry_time,
                    "estimated_wait_minutes": queue_token.estimated_wait_minutes,
                })
            except Exception:
                pass

        elif target_status == AppointmentStatus.IN_CONSULTATION:
            apt.timestamps.consultation_start_time = now
            self.queue_service.update_queue_status(
                appointment_id=apt.appointment_id,
                status=QueueStatus.IN_CONSULTATION,
                consultation_start_time=now,
            )

        elif target_status == AppointmentStatus.COMPLETED:
            apt.timestamps.consultation_end_time = now
            self.queue_service.update_queue_status(
                appointment_id=apt.appointment_id,
                status=QueueStatus.COMPLETED,
                consultation_end_time=now,
            )

        elif target_status == AppointmentStatus.CANCELLED:
            apt.timestamps.cancelled_at = now
            self.queue_service.update_queue_status(
                appointment_id=apt.appointment_id,
                status=QueueStatus.ABANDONED,
            )
            self.repo.release_slot(
                doctor_id=apt.doctor_id,
                appointment_date=apt.appointment_date,
                slot_time=apt.appointment_time,
                appointment_id=apt.appointment_id,
                patient_name=apt.patient_name,
            )
            if not apt.cancellation_details:
                apt.cancellation_details = CancellationDetails(
                    reason=request.notes or "Staff Cancellation",
                    cancelled_at=now,
                    cancelled_by=request.changed_by or "Staff Member",
                    notes=request.notes,
                )

        elif target_status == AppointmentStatus.NO_SHOW:
            self.queue_service.update_queue_status(
                appointment_id=apt.appointment_id,
                status=QueueStatus.NO_SHOW,
            )

        # Update status
        apt.status = target_status

        # Append audit history
        audit_entry = StatusAuditRecord(
            history_id=f"AUD-{apt.appointment_id}-{len(apt.history) + 1}",
            appointment_id=apt.appointment_id,
            from_status=current_status,
            to_status=target_status,
            changed_at=now,
            changed_by=request.changed_by or "Staff Member",
            notes=request.notes,
        )
        apt.history.append(audit_entry)

        return self.repo.save(apt)

    def get_slot_inventory(
        self,
        doctor_id: Optional[str] = None,
        appointment_date: Optional[date] = None,
    ) -> List[SlotInventoryItem]:
        return self.repo.get_slots(doctor_id=doctor_id, appointment_date=appointment_date)

    def get_cancellation_statistics(self) -> AppointmentStatistics:
        all_apts = self.repo.get_all()
        total = len(all_apts)
        scheduled = sum(1 for a in all_apts if a.status == AppointmentStatus.SCHEDULED)
        checked_in = sum(1 for a in all_apts if a.status == AppointmentStatus.CHECKED_IN)
        in_consultation = sum(1 for a in all_apts if a.status == AppointmentStatus.IN_CONSULTATION)
        completed = sum(1 for a in all_apts if a.status == AppointmentStatus.COMPLETED)
        cancelled = sum(1 for a in all_apts if a.status == AppointmentStatus.CANCELLED)
        no_show = sum(1 for a in all_apts if a.status == AppointmentStatus.NO_SHOW)

        completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0
        cancellation_rate = round((cancelled / total * 100), 1) if total > 0 else 0.0
        no_show_rate = round((no_show / total * 100), 1) if total > 0 else 0.0

        reasons: Dict[str, int] = {}
        for a in all_apts:
            if a.status == AppointmentStatus.CANCELLED and a.cancellation_details:
                r = a.cancellation_details.reason or "Unspecified"
                reasons[r] = reasons.get(r, 0) + 1

        released_count = self.repo.get_released_slots_count()

        return AppointmentStatistics(
            total_appointments=total,
            scheduled_count=scheduled,
            checked_in_count=checked_in,
            in_consultation_count=in_consultation,
            completed_count=completed,
            cancelled_count=cancelled,
            no_show_count=no_show,
            completion_rate=completion_rate,
            cancellation_rate=cancellation_rate,
            no_show_rate=no_show_rate,
            released_slots_count=released_count,
            reasons_breakdown=reasons,
        )

    def get_metadata(self):
        return {
            "statuses": [s.value for s in AppointmentStatus],
            "departments": DEPARTMENTS,
            "doctors": DOCTORS,
            "cancellation_reasons": [
                "Patient Request",
                "Doctor Unavailable",
                "Scheduling Conflict",
                "Medical Emergency",
                "Weather / Transportation Delay",
                "Duplicate Booking",
                "Other",
            ],
        }


appointment_service_instance = AppointmentService()

