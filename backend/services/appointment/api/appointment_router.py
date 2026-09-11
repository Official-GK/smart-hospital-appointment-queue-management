from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Query
from backend.common.schemas.response import APIResponse
from backend.services.appointment.schemas.appointment_schemas import (
    AppointmentCancelRequest,
    AppointmentCreate,
    AppointmentRescheduleRequest,
    AppointmentResponse,
    AppointmentStatistics,
    AppointmentStatus,
    FilterMetadata,
    SlotInventoryItem,
    StatusAuditRecord,
    StatusTransitionRequest,
    ScheduleConfig,
    BlockTimeRequest,
)
from backend.services.appointment.services.appointment_service import appointment_service_instance

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])


@router.get("", response_model=APIResponse[List[AppointmentResponse]])
def list_appointments(
    status: Optional[AppointmentStatus] = Query(None, description="Filter by status"),
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    doctor_id: Optional[str] = Query(None, description="Filter by doctor ID"),
    appointment_date: Optional[date] = Query(None, alias="date", description="Filter by appointment date (YYYY-MM-DD)"),
):
    appointments = appointment_service_instance.get_appointments(
        status=status,
        department_id=department_id,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
    )
    return APIResponse.ok(data=appointments, message="Appointments retrieved successfully")


@router.get("/metadata/filters", response_model=APIResponse[FilterMetadata])
def get_filter_metadata():
    metadata = appointment_service_instance.get_metadata()
    return APIResponse.ok(data=metadata, message="Filter metadata retrieved successfully")


@router.get("/statistics/summary", response_model=APIResponse[AppointmentStatistics])
def get_appointment_statistics():
    stats = appointment_service_instance.get_cancellation_statistics()
    return APIResponse.ok(data=stats, message="Appointment statistics retrieved successfully")


@router.get("/inventory/slots", response_model=APIResponse[List[SlotInventoryItem]])
def get_slot_inventory(
    doctor_id: Optional[str] = Query(None, description="Filter slots by doctor ID"),
    appointment_date: Optional[date] = Query(None, alias="date", description="Filter slots by date (YYYY-MM-DD)"),
):
    slots = appointment_service_instance.get_slot_inventory(
        doctor_id=doctor_id,
        appointment_date=appointment_date,
    )
    return APIResponse.ok(data=slots, message="Slot inventory retrieved successfully")


@router.get("/{appointment_id}", response_model=APIResponse[AppointmentResponse])
def get_appointment(appointment_id: str):
    apt = appointment_service_instance.get_appointment_by_id(appointment_id)
    return APIResponse.ok(data=apt, message="Appointment retrieved successfully")


@router.get("/{appointment_id}/history", response_model=APIResponse[List[StatusAuditRecord]])
def get_appointment_history(appointment_id: str):
    history = appointment_service_instance.get_appointment_history(appointment_id)
    return APIResponse.ok(data=history, message="Appointment history retrieved successfully")


@router.post("", response_model=APIResponse[AppointmentResponse], status_code=201)
def create_appointment(payload: AppointmentCreate):
    new_apt = appointment_service_instance.create_appointment(payload)
    return APIResponse.ok(data=new_apt, message="Appointment created successfully")


@router.patch("/{appointment_id}/status", response_model=APIResponse[AppointmentResponse])
def transition_appointment_status(appointment_id: str, request: StatusTransitionRequest):
    updated = appointment_service_instance.transition_status(appointment_id, request)
    return APIResponse.ok(data=updated, message=f"Status transitioned to '{request.new_status.value}' successfully")


@router.post("/{appointment_id}/cancel", response_model=APIResponse[AppointmentResponse])
def cancel_appointment(appointment_id: str, request: AppointmentCancelRequest):
    cancelled = appointment_service_instance.cancel_appointment(appointment_id, request)
    return APIResponse.ok(data=cancelled, message="Appointment cancelled and time slot released successfully")


@router.patch("/{appointment_id}/reschedule", response_model=APIResponse[AppointmentResponse])
def reschedule_appointment(appointment_id: str, request: AppointmentRescheduleRequest):
    updated = appointment_service_instance.reschedule_appointment(appointment_id, request)
    return APIResponse.ok(
        data=updated,
        message=f"Appointment rescheduled to {updated.appointment_date} at {updated.appointment_time} with {updated.doctor_name} successfully",
    )


@router.get("/schedules/{doctor_id}", response_model=APIResponse[ScheduleConfig])
def get_doctor_schedule(doctor_id: str):
    schedule = appointment_service_instance.get_schedule(doctor_id)
    return APIResponse.ok(data=schedule, message="Doctor schedule retrieved successfully")


@router.put("/schedules/{doctor_id}", response_model=APIResponse[ScheduleConfig])
def update_doctor_schedule(doctor_id: str, config: ScheduleConfig):
    updated = appointment_service_instance.update_schedule(doctor_id, config)
    return APIResponse.ok(data=updated, message="Doctor schedule updated successfully")


@router.post("/schedules/{doctor_id}/block", response_model=APIResponse[ScheduleConfig])
def block_doctor_time(doctor_id: str, request: BlockTimeRequest):
    updated = appointment_service_instance.add_blocked_time(doctor_id, request)
    return APIResponse.ok(data=updated, message="Time blocked successfully")


