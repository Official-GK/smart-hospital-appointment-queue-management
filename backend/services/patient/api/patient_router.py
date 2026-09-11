from typing import List, Optional
from fastapi import APIRouter, Query, status
from backend.common.schemas.response import APIResponse
from backend.services.patient.schemas.patient_schemas import (
    EligibleCheckInItem,
    PatientCheckInRequest,
    PatientCheckInResponse,
    PatientCreate,
    PatientResponse,
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
