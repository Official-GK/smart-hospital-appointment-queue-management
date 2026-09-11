from typing import List, Optional
from fastapi import APIRouter, Query, Depends, Request
from backend.common.security import RoleChecker, get_optional_user, get_current_user
from backend.common.pii_masking import mask_sensitive_data
from backend.common.audit_logger import log_action
from backend.common.schemas.response import APIResponse
from backend.services.queue.schemas.queue_schemas import QueueToken, QueueStatusUpdateRequest
from backend.services.queue.services.queue_service import queue_service_instance

router = APIRouter(prefix="/api/queue", tags=["Queue"])


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
        
    log_action(
        employee_id=user["employee_id"], 
        action="QUEUE_OVERRIDE", 
        details={"appointment_id": appointment_id, "new_status": payload.status.value}, 
        ip_address=request.client.host if request.client else None
    )
    
    return APIResponse.ok(data=updated_token, message=f"Queue status updated to '{payload.status.value}' successfully")
