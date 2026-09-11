from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Query, Depends, Request
from backend.common.schemas.response import APIResponse
from backend.common.security import RoleChecker, get_optional_user, get_current_user
from backend.common.pii_masking import mask_sensitive_data
from backend.common.audit_logger import log_action
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


@router.get("")
def list_appointments(
    status: Optional[AppointmentStatus] = Query(None, description="Filter by status"),
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    doctor_id: Optional[str] = Query(None, description="Filter by doctor ID"),
    appointment_date: Optional[date] = Query(None, alias="date", description="Filter by appointment date (YYYY-MM-DD)"),
    user: dict = Depends(get_optional_user)
):
    appointments = appointment_service_instance.get_appointments(
        status=status,
        department_id=department_id,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
    )
    masked_appointments = mask_sensitive_data(appointments, user)
    return APIResponse.ok(data=masked_appointments, message="Appointments retrieved successfully")


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


@router.get("/{appointment_id}")
def get_appointment(appointment_id: str, user: dict = Depends(get_optional_user)):
    apt = appointment_service_instance.get_appointment_by_id(appointment_id)
    masked_apt = mask_sensitive_data(apt, user)
    return APIResponse.ok(data=masked_apt, message="Appointment retrieved successfully")


@router.get("/{appointment_id}/history", response_model=APIResponse[List[StatusAuditRecord]])
def get_appointment_history(appointment_id: str):
    history = appointment_service_instance.get_appointment_history(appointment_id)
    return APIResponse.ok(data=history, message="Appointment history retrieved successfully")


@router.post("", response_model=APIResponse[AppointmentResponse], dependencies=[Depends(RoleChecker(["admin", "staff"]))])
def create_appointment(request: Request, payload: AppointmentCreate, user: dict = Depends(get_current_user)):
    apt = appointment_service_instance.create_appointment(payload)
    
    log_action(
        employee_id=user["employee_id"], 
        action="CREATE_APPOINTMENT", 
        details={"appointment_id": apt.appointment_id, "department_id": apt.department_id}, 
        ip_address=request.client.host if request.client else None
    )
    
    return APIResponse.ok(data=apt, message="Appointment booked successfully")


@router.patch("/{appointment_id}/status", response_model=APIResponse[AppointmentResponse], dependencies=[Depends(RoleChecker(["admin", "staff"]))])
def transition_appointment_status(req: Request, appointment_id: str, request: StatusTransitionRequest, user: dict = Depends(get_current_user)):
    updated = appointment_service_instance.transition_status(appointment_id, request)
    
    log_action(
        employee_id=user["employee_id"], 
        action="UPDATE_APPOINTMENT_STATUS", 
        details={"appointment_id": appointment_id, "new_status": request.new_status.value}, 
        ip_address=req.client.host if req.client else None
    )
    
    return APIResponse.ok(data=updated, message=f"Status transitioned to '{request.new_status.value}' successfully")


@router.post("/{appointment_id}/cancel", response_model=APIResponse[AppointmentResponse], dependencies=[Depends(RoleChecker(["admin", "staff"]))])
def cancel_appointment(appointment_id: str, request: AppointmentCancelRequest):
    cancelled = appointment_service_instance.cancel_appointment(appointment_id, request)
    return APIResponse.ok(data=cancelled, message="Appointment cancelled and time slot released successfully")


@router.patch("/{appointment_id}/reschedule", response_model=APIResponse[AppointmentResponse], dependencies=[Depends(RoleChecker(["admin", "staff"]))])
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


@router.put("/schedules/{doctor_id}", response_model=APIResponse[ScheduleConfig], dependencies=[Depends(RoleChecker(["admin", "staff"]))])
def update_doctor_schedule(doctor_id: str, config: ScheduleConfig):
    updated = appointment_service_instance.update_schedule(doctor_id, config)
    return APIResponse.ok(data=updated, message="Doctor schedule updated successfully")


@router.post("/schedules/{doctor_id}/block", response_model=APIResponse[ScheduleConfig], dependencies=[Depends(RoleChecker(["admin", "staff"]))])
def block_doctor_time(doctor_id: str, request: BlockTimeRequest):
    updated = appointment_service_instance.add_blocked_time(doctor_id, request)
    return APIResponse.ok(data=updated, message="Time blocked successfully")


