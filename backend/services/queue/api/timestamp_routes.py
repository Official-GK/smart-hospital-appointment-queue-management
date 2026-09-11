from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Query, status

from backend.common.schemas.response import APIResponse
from backend.services.queue.schemas.timestamp_schemas import (
    TimestampRecordCreate,
    TimestampRecordResponse,
    TokenTimelineResponse,
    OperationalAnalyticsResponse,
)
from backend.services.queue.services.timestamp_service import timestamp_service

router = APIRouter(prefix="/timestamps", tags=["Queue Operational Timestamps"])


@router.post("", response_model=APIResponse[TimestampRecordResponse], status_code=status.HTTP_201_CREATED)
def record_operational_timestamp(payload: TimestampRecordCreate):
    """
    Immutably captures a timestamp for a patient journey stage.
    Covers: Registration, Booking, Check-In, Token Issued, Called, Consultation Start/End, Completion.
    """
    record = timestamp_service.record_timestamp(payload)
    return APIResponse.ok(
        data=record,
        message=f"Timestamp for stage '{payload.stage.value}' recorded successfully",
    )


@router.get("/token/{token_id}", response_model=APIResponse[TokenTimelineResponse])
def get_token_timeline(token_id: str):
    """
    Retrieves the complete immutable audit trail of timestamps and computed duration metrics
    (waiting time, consultation duration, total journey time) for a token.
    """
    timeline = timestamp_service.get_token_timeline(token_id)
    return APIResponse.ok(
        data=timeline,
        message=f"Timeline for token '{token_id}' retrieved successfully",
    )


@router.get("/patient/{patient_id}", response_model=APIResponse[List[TimestampRecordResponse]])
def get_patient_history(patient_id: str):
    """
    Retrieves all immutable timestamp records captured across visits for a patient.
    """
    history = timestamp_service.get_patient_history(patient_id)
    return APIResponse.ok(
        data=history,
        message=f"Journey history for patient '{patient_id}' retrieved successfully",
    )


@router.get("/analytics/summary", response_model=APIResponse[OperationalAnalyticsResponse])
def get_operational_analytics(
    start_time: Optional[datetime] = Query(None, description="Start time filter (UTC)"),
    end_time: Optional[datetime] = Query(None, description="End time filter (UTC)"),
):
    """
    Provides aggregated operational metrics (waiting times, consultation times, doctor throughput,
    stage distributions) for management reports and operational dashboards.
    """
    analytics = timestamp_service.get_operational_analytics(start_time=start_time, end_time=end_time)
    return APIResponse.ok(
        data=analytics,
        message="Operational analytics retrieved successfully",
    )
