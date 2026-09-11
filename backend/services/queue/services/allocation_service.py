from typing import Optional, Dict, List, Set
from fastapi import HTTPException

from backend.services.queue.models.doctor_workload_models import (
    DoctorAvailability,
    DoctorWorkloadRecord,
    doctor_workload_store,
)
from backend.services.queue.schemas.queue_schemas import QueueStatus, QueueToken
from backend.services.queue.schemas.allocation_schemas import (
    DoctorAllocationSuggestion,
    DoctorAllocationSuggestResponse,
)
from backend.services.queue.services.queue_service import queue_service_instance
from backend.services.queue.services.waiting_time_service import waiting_time_service_instance
from backend.database.demo_data import DOCTORS
from backend.database.token_fetcher import save_token


class AllocationService:
    """
    Service responsible for ranking eligible doctors by suitability and executing staff assignments.
    Implements the SRS staff-confirms-final-assignment model.
    """

    def suggest_doctor_allocations(
        self,
        department_id: str,
        token_id: Optional[str] = None,
    ) -> DoctorAllocationSuggestResponse:
        """
        Acceptance Criteria 1, 2, 3:
        Ranks eligible doctors matching the required department specialty:
        - Excludes doctors marked OFF_DUTY or ABSENT.
        - Measures current active queue lengths (WAITING + CALLED).
        - Sorts by ascending queue length (lightest load first), then availability.
        - Staff reviews and makes the final binding selection.
        """
        # 1. Discover all candidate doctors for this department specialty
        candidate_doctors: Dict[str, Dict[str, str]] = {}

        # From demo data repository
        for d in DOCTORS:
            if d.get("department_id") == department_id:
                candidate_doctors[d["doctor_id"]] = {
                    "doctor_id": d["doctor_id"],
                    "doctor_name": d["doctor_name"],
                    "department_id": department_id,
                }

        # From doctor workload store
        for doc_rec in doctor_workload_store.get_doctors_by_department(department_id):
            candidate_doctors[doc_rec.doctor_id] = {
                "doctor_id": doc_rec.doctor_id,
                "doctor_name": doc_rec.doctor_name,
                "department_id": department_id,
            }

        # From active tokens
        with queue_service_instance._lock:
            for t in queue_service_instance._tokens.values():
                if t.department_id == department_id and t.doctor_id:
                    if t.doctor_id not in candidate_doctors:
                        candidate_doctors[t.doctor_id] = {
                            "doctor_id": t.doctor_id,
                            "doctor_name": t.doctor_name,
                            "department_id": department_id,
                        }

        # 2. Filter, measure queue length, and check availability
        suggestions: List[DoctorAllocationSuggestion] = []

        for doc_id, doc_info in candidate_doctors.items():
            workload_rec = doctor_workload_store.get_doctor_workload(doc_id)
            current_availability = workload_rec.availability if workload_rec else DoctorAvailability.AVAILABLE

            # Acceptance Criteria 3: Exclude Absent or Off-Duty doctors
            if current_availability in {DoctorAvailability.OFF_DUTY, DoctorAvailability.ABSENT}:
                continue

            # Acceptance Criteria 2: Measure current queue length (WAITING + CALLED)
            with queue_service_instance._lock:
                active_tokens = [
                    t for t in queue_service_instance._tokens.values()
                    if t.doctor_id == doc_id and t.status in {QueueStatus.WAITING, QueueStatus.CALLED}
                ]
            queue_length = len(active_tokens)

            # Compute estimated wait minutes for next arrival
            avg_duration, _ = waiting_time_service_instance.get_average_consultation_duration(
                doctor_id=doc_id,
                department_id=department_id,
            )
            estimated_wait = int(round(queue_length * avg_duration))
            completed_today = workload_rec.completed_consultations_count if workload_rec else 0

            suggestions.append(
                DoctorAllocationSuggestion(
                    doctor_id=doc_id,
                    doctor_name=doc_info["doctor_name"],
                    department_id=department_id,
                    availability=current_availability.value,
                    active_queue_length=queue_length,
                    estimated_wait_minutes=estimated_wait,
                    completed_today_count=completed_today,
                    is_recommended=False,
                    suitability_reason="Eligible specialist",
                )
            )

        # 3. Sort doctors by ascending queue length (lightest load first)
        def sort_key(s: DoctorAllocationSuggestion):
            availability_weight = 0 if s.availability == DoctorAvailability.AVAILABLE.value else 1
            return (s.active_queue_length, availability_weight, s.completed_today_count)

        suggestions.sort(key=sort_key)

        # 4. Mark the #1 candidate as recommended
        if suggestions:
            top = suggestions[0]
            top.is_recommended = True
            if top.active_queue_length == 0:
                top.suitability_reason = "Recommended: Immediate availability with zero waiting patients"
            else:
                top.suitability_reason = f"Recommended: Lightest queue load ({top.active_queue_length} patients ahead)"

            for other in suggestions[1:]:
                other.suitability_reason = f"Alternative: Current queue load of {other.active_queue_length} patient(s)"

        return DoctorAllocationSuggestResponse(
            department_id=department_id,
            total_eligible_doctors=len(suggestions),
            suggestions=suggestions,
        )

    def assign_doctor_to_token(
        self,
        token_identifier: str,
        doctor_id: str,
        recorded_by_user_id: str,
        notes: Optional[str] = None,
    ) -> QueueToken:
        """
        Acceptance Criteria 4:
        Staff confirms doctor assignment or manually overrides/reassigns patient to another available doctor.
        - Validates the target doctor is available (not OFF_DUTY or ABSENT).
        - Updates token assignment.
        - Dynamically recalculates wait times for both the old and new doctor's queues.
        """
        # 1. Lookup token
        token = self._find_token(token_identifier)
        if not token:
            raise HTTPException(status_code=404, detail=f"Token '{token_identifier}' not found in queue")

        # 2. Acceptance Criteria 3: Validate chosen doctor is NOT Absent or Off-Duty
        doc_rec = doctor_workload_store.get_doctor_workload(doctor_id)
        if doc_rec and doc_rec.availability in {DoctorAvailability.OFF_DUTY, DoctorAvailability.ABSENT}:
            raise HTTPException(
                status_code=422,
                detail=f"Cannot assign patient to doctor '{doctor_id}' because doctor is currently {doc_rec.availability.value}. "
                       f"Doctors marked Absent or Off-Duty cannot receive new patient allocations.",
            )

        # 3. Determine doctor name
        doctor_name = None
        if doc_rec:
            doctor_name = doc_rec.doctor_name
        else:
            demo_match = next((d["doctor_name"] for d in DOCTORS if d["doctor_id"] == doctor_id), None)
            doctor_name = demo_match or f"Doctor {doctor_id}"

        old_doctor_id = token.doctor_id

        # 4. Perform assignment / override
        with queue_service_instance._lock:
            token.doctor_id = doctor_id
            token.doctor_name = doctor_name

        # 5. Acceptance Criteria 2 & 4: Recalculate wait times for both queues
        if old_doctor_id and old_doctor_id != doctor_id:
            waiting_time_service_instance.recalculate_queue_wait_times(
                doctor_id=old_doctor_id,
                department_id=token.department_id,
            )

        waiting_time_service_instance.recalculate_queue_wait_times(
            doctor_id=doctor_id,
            department_id=token.department_id,
        )

        # Update token's own wait time
        wait_info = waiting_time_service_instance.calculate_token_wait_time(token.token_id)
        token.estimated_wait_minutes = wait_info.estimated_wait_minutes

        # Persist to database if connected
        try:
            save_token({
                "token_id": token.token_id,
                "doctor_id": token.doctor_id,
                "doctor_name": token.doctor_name,
                "estimated_wait_minutes": token.estimated_wait_minutes,
            })
        except Exception:
            pass

        return token

    def _find_token(self, token_identifier: str) -> Optional[QueueToken]:
        with queue_service_instance._lock:
            for t in queue_service_instance._tokens.values():
                if t.token_id == token_identifier or t.appointment_id == token_identifier:
                    return t
        return queue_service_instance.get_token_by_appointment(token_identifier)


allocation_service_instance = AllocationService()
