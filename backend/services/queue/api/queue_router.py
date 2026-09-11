from typing import List, Optional
from fastapi import APIRouter, Query, Depends, Request
from backend.common.security import RoleChecker, get_optional_user, get_current_user
from backend.common.pii_masking import mask_sensitive_data
from backend.common.audit_logger import log_action
from backend.common.schemas.response import APIResponse
from backend.services.queue.schemas.queue_schemas import QueueToken, QueueStatusUpdateRequest
from backend.services.queue.services.queue_service import queue_service_instance

from backend.services.queue.api.timestamp_routes import router as timestamp_router

router = APIRouter(prefix="/api/queue", tags=["Queue"])
router.include_router(timestamp_router)


@router.get("/live")
def get_live_queue(
    department_id: Optional[str] = Query(None, description="Filter by department"),
    doctor_id: Optional[str] = Query(None, description="Filter by doctor"),
    user: dict = Depends(get_optional_user)
):
    tokens = queue_service_instance.get_live_queue(department_id=department_id, doctor_id=doctor_id)
    masked_tokens = mask_sensitive_data(tokens, user)
    return APIResponse.ok(data=masked_tokens, message="Live queue retrieved successfully")


@router.patch("/{appointment_id}/status", response_model=APIResponse[QueueToken], dependencies=[Depends(RoleChecker(["admin", "staff"]))])
def update_queue_status(request: Request, appointment_id: str, payload: QueueStatusUpdateRequest, user: dict = Depends(get_current_user)):
    from fastapi import HTTPException
    updated_token = queue_service_instance.update_queue_status(
        appointment_id=appointment_id,
        status=payload.status
    )
    if not updated_token:
        raise HTTPException(status_code=404, detail=f"Token not found for appointment ID '{appointment_id}'")
    return APIResponse.ok(data=updated_token, message=f"Queue status updated to '{request.status.value}' successfully")


from backend.services.queue.schemas.abandonment_schemas import (
    AbandonmentRequest,
    AbandonmentRecordResponse,
    AbandonmentAnalyticsResponse,
)
from backend.services.queue.services.abandonment_service import abandonment_service_instance



@router.patch("/{token_id}/abandon", response_model=APIResponse[AbandonmentRecordResponse])
def abandon_patient_token(token_id: str, request: AbandonmentRequest):
    """
    Flags a WAITING patient as Abandoned.
    - Validates patient is currently WAITING.
    - Records an immutable timestamp with elapsed waiting duration.
    - Removes patient from live queue and recalculates wait times for remaining patients.
    """
    result = abandonment_service_instance.abandon_patient(
        token_identifier=token_id,
        reason=request.reason,
        recorded_by_user_id=request.recorded_by_user_id,
    )
    return APIResponse.ok(
        data=result,
        message=f"Patient token '{result.token.token_number}' flagged as abandoned successfully",
    )


@router.get("/analytics/abandonment", response_model=APIResponse[AbandonmentAnalyticsResponse])
def get_abandonment_analytics(
    department_id: Optional[str] = Query(None, description="Filter by department"),
    doctor_id: Optional[str] = Query(None, description="Filter by doctor"),
):
    """
    Returns aggregated abandonment metrics (counts, rates, and average waiting time before abandonment)
    for hospital management reporting.
    """
    analytics = abandonment_service_instance.get_abandonment_analytics(
        department_id=department_id,
        doctor_id=doctor_id,
    )
    return APIResponse.ok(
        data=analytics,
        message="Abandonment analytics retrieved successfully",
    )


from backend.services.queue.schemas.no_show_schemas import (
    NoShowRequest,
    NoShowRecordResponse,
    NoShowAnalyticsResponse,
    PatientNoShowHistoryResponse,
)
from backend.services.queue.services.no_show_service import no_show_service_instance


@router.patch("/{token_id}/no-show", response_model=APIResponse[NoShowRecordResponse])
def mark_patient_no_show(token_id: str, request: NoShowRequest):
    """
    Marks a patient as No-Show when they fail to appear after being called.
    - Validates patient status is CALLED.
    - Records an immutable timestamp with recorded_by_user_id.
    - Removes patient from live queue sequence and logs to patient history.
    """
    result = no_show_service_instance.mark_no_show(
        token_identifier=token_id,
        recorded_by_user_id=request.get_recorded_by_user_id(),
        reason=request.reason,
    )
    return APIResponse.ok(
        data=result,
        message=f"Patient token '{result.token.token_number}' marked as No-Show successfully",
    )


@router.get("/analytics/no-show", response_model=APIResponse[NoShowAnalyticsResponse])
def get_no_show_analytics(
    department_id: Optional[str] = Query(None, description="Filter by department"),
    doctor_id: Optional[str] = Query(None, description="Filter by doctor"),
):
    """
    Returns aggregated no-show metrics across doctors and departments for management reporting.
    """
    analytics = no_show_service_instance.get_no_show_analytics(
        department_id=department_id,
        doctor_id=doctor_id,
    )
    return APIResponse.ok(
        data=analytics,
        message="No-show analytics retrieved successfully",
    )


@router.get("/patients/{patient_id}/no-shows", response_model=APIResponse[PatientNoShowHistoryResponse])
def get_patient_no_show_history(patient_id: str):
    """
    Retrieves all historical no-show events logged for a specific patient profile.
    """
    history = no_show_service_instance.get_patient_no_show_history(patient_id=patient_id)
    return APIResponse.ok(
        data=history,
        message="Patient no-show history retrieved successfully",
    )


from backend.services.queue.schemas.completion_schemas import (
    CompletionRequest,
    CompletionRecordResponse,
    CompletedAnalyticsResponse,
    PatientVisitHistoryResponse,
    DoctorWorkloadResponse,
)
from backend.services.queue.services.completion_service import completion_service_instance


@router.patch("/{token_id}/complete", response_model=APIResponse[CompletionRecordResponse])
def complete_patient_consultation(token_id: str, request: CompletionRequest):
    """
    Doctor action to conclude a consultation.
    - Validates status is IN_CONSULTATION.
    - Transitions token to COMPLETED and computes total consultation time.
    - Removes token from live queue views and archives to visit history.
    - Updates doctor workload metrics and resets doctor availability to AVAILABLE.
    """
    result = completion_service_instance.complete_consultation(
        token_identifier=token_id,
        recorded_by_user_id=request.recorded_by_user_id,
        notes=request.notes,
    )
    return APIResponse.ok(
        data=result,
        message=f"Consultation for token '{result.token.token_number}' completed successfully",
    )


@router.get("/analytics/completed", response_model=APIResponse[CompletedAnalyticsResponse])
def get_completed_analytics(
    department_id: Optional[str] = Query(None, description="Filter by department"),
    doctor_id: Optional[str] = Query(None, description="Filter by doctor"),
):
    """
    Returns aggregated consultation completion metrics (counts, average duration) for management.
    """
    analytics = completion_service_instance.get_completion_analytics(
        department_id=department_id,
        doctor_id=doctor_id,
    )
    return APIResponse.ok(
        data=analytics,
        message="Completed consultation analytics retrieved successfully",
    )


@router.get("/patients/{patient_id}/visits", response_model=APIResponse[PatientVisitHistoryResponse])
def get_patient_visit_history(patient_id: str):
    """
    Retrieves the archived visit history records for a patient.
    """
    visits = completion_service_instance.get_patient_visits(patient_id=patient_id)
    return APIResponse.ok(
        data=visits,
        message="Patient visit history retrieved successfully",
    )


@router.get("/doctors/{doctor_id}/workload", response_model=APIResponse[DoctorWorkloadResponse])
def get_doctor_workload_status(doctor_id: str):
    """
    Retrieves current doctor workload metrics and availability state.
    """
    workload = completion_service_instance.get_doctor_workload(doctor_id=doctor_id)
    return APIResponse.ok(
        data=workload,
        message="Doctor workload retrieved successfully",
    )


from backend.services.queue.schemas.waiting_time_schemas import WaitTimeResponse
from backend.services.queue.services.waiting_time_service import waiting_time_service_instance


@router.get("/{token_id}/wait-time", response_model=APIResponse[WaitTimeResponse])
def get_patient_estimated_wait_time(token_id: str):
    """
    Returns the real-time estimated waiting time for a patient token ticket / queue screen.
    Calculation: (Patients Ahead) × (Average Consultation Duration).
    """
    wait_time = waiting_time_service_instance.calculate_token_wait_time(token_identifier=token_id)
    return APIResponse.ok(
        data=wait_time,
        message=f"Estimated wait time for token '{wait_time.token_number}' retrieved successfully",
    )


from backend.services.queue.schemas.allocation_schemas import (
    DoctorAllocationSuggestResponse,
    DoctorAssignmentRequest,
    DoctorAvailabilityUpdateRequest,
)
from backend.services.queue.services.allocation_service import allocation_service_instance
from backend.services.queue.models.doctor_workload_models import doctor_workload_store


@router.get("/allocation/suggest", response_model=APIResponse[DoctorAllocationSuggestResponse])
def suggest_doctor_allocations(
    department_id: str = Query(..., description="Department specialty ID to rank doctors for"),
    token_id: Optional[str] = Query(None, description="Optional patient token ID"),
):
    """
    Ranks eligible doctors for a department specialty based on lightest workload and availability.
    Staff reviews the ranked suggestions and makes the final assignment.
    """
    suggestions = allocation_service_instance.suggest_doctor_allocations(
        department_id=department_id,
        token_id=token_id,
    )
    return APIResponse.ok(
        data=suggestions,
        message=f"Found {suggestions.total_eligible_doctors} eligible doctor(s) ranked for department '{department_id}'",
    )


@router.patch("/{token_id}/assign-doctor", response_model=APIResponse[QueueToken])
def assign_doctor_to_token(token_id: str, request: DoctorAssignmentRequest):
    """
    Staff confirms doctor assignment or manually overrides/reassigns a patient to another doctor.
    - Validates chosen doctor is available (not Absent or Off-Duty).
    - Updates patient token doctor assignment.
    - Recalculates waiting times for both old and new doctor queues dynamically.
    """
    updated_token = allocation_service_instance.assign_doctor_to_token(
        token_identifier=token_id,
        doctor_id=request.doctor_id,
        recorded_by_user_id=request.recorded_by_user_id,
        notes=request.notes,
    )
    return APIResponse.ok(
        data=updated_token,
        message=f"Patient token '{updated_token.token_number}' successfully assigned to doctor '{updated_token.doctor_name}'",
    )


@router.patch("/doctors/{doctor_id}/availability", response_model=APIResponse[DoctorWorkloadResponse])
def update_doctor_availability(doctor_id: str, request: DoctorAvailabilityUpdateRequest):
    """
    Updates a doctor's availability state (AVAILABLE, BUSY, OFF_DUTY, ABSENT).
    Doctors marked OFF_DUTY or ABSENT are excluded from allocation suggestions.
    """
    doc_rec = doctor_workload_store.set_availability(
        doctor_id=doctor_id,
        availability=request.availability,
        doctor_name=request.doctor_name,
        department_id=request.department_id,
    )
    return APIResponse.ok(
        data=DoctorWorkloadResponse(
            doctor_id=doc_rec.doctor_id,
            doctor_name=doc_rec.doctor_name,
            availability=doc_rec.availability.value,
            completed_consultations_count=doc_rec.completed_consultations_count,
            total_consultation_seconds=doc_rec.total_consultation_seconds,
            last_completed_at=doc_rec.last_completed_at,
        ),
        message=f"Doctor '{doctor_id}' availability updated to '{request.availability.value}'",
    )


from backend.services.queue.schemas.priority_schemas import (
    PriorityElevationRequest,
    PriorityElevationResponse,
)
from backend.services.queue.services.priority_service import priority_service_instance


@router.patch("/{token_id}/priority", response_model=APIResponse[PriorityElevationResponse])
def elevate_patient_priority(token_id: str, request: PriorityElevationRequest):
    """
    Staff action to manually elevate a patient's queue priority with a mandatory reason.
    - Validates non-empty reason entry.
    - Updates token priority and populates visual badge metadata.
    - Records an immutable audit record in timestamp_store.
    - Re-orders queue and triggers dynamic wait-time recalculation.
    """
    result = priority_service_instance.elevate_priority(
        token_identifier=token_id,
        priority=request.priority,
        reason=request.reason,
        recorded_by_user_id=request.recorded_by_user_id,
    )
    return APIResponse.ok(
        data=result,
        message=f"Priority for token '{result.token.token_number}' elevated to '{result.new_priority}' successfully",
    )





        
    log_action(
        employee_id=user["employee_id"], 
        action="QUEUE_OVERRIDE", 
        details={"appointment_id": appointment_id, "new_status": payload.status.value}, 
        ip_address=request.client.host if request.client else None
    )
    
    return APIResponse.ok(data=updated_token, message=f"Queue status updated to '{payload.status.value}' successfully")
