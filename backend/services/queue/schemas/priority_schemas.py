from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from backend.services.queue.schemas.queue_schemas import QueuePriority, QueueToken


class PriorityElevationRequest(BaseModel):
    """Payload to manually elevate a patient's queue priority with a mandatory clinical/staff reason."""
    priority: QueuePriority = Field(..., description="Target elevated priority category")
    reason: str = Field(..., description="Mandatory explanation for manual elevation", min_length=1, json_schema_extra={"example": "Severe chest pain reported at counter"})
    recorded_by_user_id: str = Field(..., description="ID of staff member elevating priority", json_schema_extra={"example": "STAFF-TRIAGE-01"})


class PriorityElevationResponse(BaseModel):
    """Response returned when a token's priority has been successfully elevated."""
    token: QueueToken
    previous_priority: str
    new_priority: str
    reason: str
    recorded_by_user_id: str
    elevated_at: datetime
