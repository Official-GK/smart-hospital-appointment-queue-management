from typing import List, Optional
from fastapi import APIRouter, Query
from backend.common.schemas.response import APIResponse
from backend.services.queue.schemas.queue_schemas import QueueToken, QueueStatusUpdateRequest
from backend.services.queue.services.queue_service import queue_service_instance

router = APIRouter(prefix="/api/queue", tags=["Queue"])


@router.get("/live", response_model=APIResponse[List[QueueToken]])
def get_live_queue(
    department_id: Optional[str] = Query(None, description="Filter by department"),
    doctor_id: Optional[str] = Query(None, description="Filter by doctor"),
):
    tokens = queue_service_instance.get_live_queue(department_id=department_id, doctor_id=doctor_id)
    return APIResponse.ok(data=tokens, message="Live queue retrieved successfully")


@router.patch("/{appointment_id}/status", response_model=APIResponse[QueueToken])
def update_queue_status(appointment_id: str, request: QueueStatusUpdateRequest):
    from fastapi import HTTPException
    updated_token = queue_service_instance.update_queue_status(
        appointment_id=appointment_id,
        status=request.status
    )
    if not updated_token:
        raise HTTPException(status_code=404, detail=f"Token not found for appointment ID '{appointment_id}'")
    return APIResponse.ok(data=updated_token, message=f"Queue status updated to '{request.status.value}' successfully")
