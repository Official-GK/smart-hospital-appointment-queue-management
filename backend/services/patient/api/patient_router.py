from typing import List, Optional
from fastapi import APIRouter, Header, Query, status
from backend.common.schemas.response import APIResponse
from backend.services.patient.schemas.patient_schemas import (
    EligibleCheckInItem,
    PatientCheckInRequest,
    PatientCheckInResponse,
    PatientCreate,
    PatientResponse,
    PatientProfileResponse,
    PatientUpdateRequest,
    PatientAuditRecord,
)
from backend.services.patient.services.patient_service import patient_service_instance

router = APIRouter(prefix="/api/patients", tags=["Patients"])


@router.post("/check-in", response_model=APIResponse[PatientCheckInResponse], status_code=status.HTTP_200_OK)
def check_in_patient(payload: PatientCheckInRequest):
    """
    Execute physical arrival check-in for a patient (appointment or walk-in).
    - Records arrival timestamp
    - Updates patient and appointment status to Checked-In
    - Immediately enqueues into the active queue with assigned token
    """
    receipt = patient_service_instance.check_in_patient(payload)
    return APIResponse.ok(
        data=receipt,
        message=f"Patient '{receipt.patient_name}' successfully checked in. Token: {receipt.token_number or 'Pending'}",
    )


@router.get("/check-in/eligible", response_model=APIResponse[List[EligibleCheckInItem]])
def get_eligible_check_ins():
    """
    Retrieve patients with scheduled appointments who are eligible for front-desk check-in.
    """
    eligible = patient_service_instance.get_eligible_check_ins()
    return APIResponse.ok(data=eligible, message="Eligible check-in appointments retrieved successfully")


@router.get("", response_model=APIResponse[List[PatientResponse]])
def list_patients(query: Optional[str] = Query(None, description="Search by name, patient ID, or phone")):
    """
    List or search patient demographic records.
    """
    if query:
        patients = patient_service_instance.search_patients(query)
    else:
        patients = patient_service_instance.get_all_patients()
    return APIResponse.ok(data=patients, message="Patients retrieved successfully")


@router.get("/{patient_id}", response_model=APIResponse[PatientResponse])
def get_patient(patient_id: str):
    """
    Retrieve a patient by ID.
    """
    patient = patient_service_instance.get_patient_by_id(patient_id)
    return APIResponse.ok(data=patient, message="Patient retrieved successfully")


@router.post("", response_model=APIResponse[PatientResponse], status_code=status.HTTP_201_CREATED)
def register_patient(payload: PatientCreate):
    """
    Register a new patient.
    """
    new_patient = patient_service_instance.create_patient(payload)
    return APIResponse.ok(data=new_patient, message=f"Patient '{new_patient.patient_name}' registered successfully")


@router.get("/{patient_id}/profile", response_model=APIResponse[PatientProfileResponse])
def get_patient_profile(
    patient_id: str,
    mask_sensitive: bool = Query(False, description="Whether to mask phone number and address"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role", description="Staff role for authorization"),
):
    """
    Retrieve comprehensive patient profile including active appointments, visit history,
    token history, and operational timestamps. Supports role-based privacy masking.
    """
    role = x_user_role or "Staff"
    profile = patient_service_instance.get_patient_profile(
        patient_id=patient_id,
        role=role,
        mask_sensitive=mask_sensitive,
    )
    return APIResponse.ok(data=profile, message="Patient profile retrieved successfully")


@router.put("/{patient_id}", response_model=APIResponse[PatientResponse])
def update_patient_details(patient_id: str, payload: PatientUpdateRequest):
    """
    Update demographic and contact information with field-level audit trail.
    """
    updated_patient, audits = patient_service_instance.update_patient_details(patient_id, payload)
    return APIResponse.ok(
        data=updated_patient,
        message=f"Patient '{updated_patient.patient_name}' updated successfully ({len(audits)} field(s) modified)",
    )


@router.get("/{patient_id}/audit", response_model=APIResponse[List[PatientAuditRecord]])
def get_patient_audit_history(patient_id: str):
    """
    Retrieve demographic modification audit trail for a patient.
    """
    audits = patient_service_instance.get_patient_audit_trail(patient_id)
    return APIResponse.ok(data=audits, message="Patient audit trail retrieved successfully")

