import uuid
from datetime import date, datetime
from typing import Dict, List, Optional
from backend.services.patient.schemas.patient_schemas import (
    PatientCreate,
    PatientResponse,
    PatientStatus,
)


class PatientRepository:
    """
    In-memory repository for patient demographics and status tracking.
    """

    def __init__(self):
        self._patients: Dict[str, PatientResponse] = {}
        self._seed_patients()

    def _seed_patients(self):
        initial_patients = [
            PatientResponse(
                patient_id="PAT-001",
                first_name="James",
                last_name="Wilson",
                patient_name="James Wilson",
                date_of_birth=date(1985, 4, 12),
                gender="Male",
                phone="+1-555-0101",
                address="124 Oak Street, Springfield",
                status=PatientStatus.REGISTERED,
                created_at=datetime(2026, 8, 1, 9, 0),
            ),
            PatientResponse(
                patient_id="PAT-002",
                first_name="Michael",
                last_name="Chen",
                patient_name="Michael Chen",
                date_of_birth=date(1990, 8, 23),
                gender="Male",
                phone="+1-555-0102",
                address="452 Elm Street, Springfield",
                status=PatientStatus.CHECKED_IN,
                created_at=datetime(2026, 8, 2, 10, 0),
                last_arrival_time=datetime(2026, 9, 10, 9, 30),
            ),
            PatientResponse(
                patient_id="PAT-003",
                first_name="Elena",
                last_name="Rodriguez",
                patient_name="Elena Rodriguez",
                date_of_birth=date(1978, 11, 5),
                gender="Female",
                phone="+1-555-0103",
                address="789 Pine Road, Springfield",
                status=PatientStatus.IN_CONSULTATION,
                created_at=datetime(2026, 8, 3, 11, 30),
                last_arrival_time=datetime(2026, 9, 10, 9, 0),
            ),
            PatientResponse(
                patient_id="PAT-004",
                first_name="Robert",
                last_name="Taylor",
                patient_name="Robert Taylor",
                date_of_birth=date(1965, 2, 17),
                gender="Male",
                phone="+1-555-0104",
                address="321 Maple Avenue, Springfield",
                status=PatientStatus.COMPLETED,
                created_at=datetime(2026, 8, 4, 14, 0),
            ),
            PatientResponse(
                patient_id="PAT-005",
                first_name="Sophia",
                last_name="Martinez",
                patient_name="Sophia Martinez",
                date_of_birth=date(1995, 6, 30),
                gender="Female",
                phone="+1-555-0105",
                address="654 Cedar Blvd, Springfield",
                status=PatientStatus.REGISTERED,
                created_at=datetime(2026, 8, 5, 8, 45),
            ),
            PatientResponse(
                patient_id="PAT-006",
                first_name="David",
                last_name="Kim",
                patient_name="David Kim",
                date_of_birth=date(1988, 9, 14),
                gender="Male",
                phone="+1-555-0106",
                address="987 Birch Lane, Springfield",
                status=PatientStatus.REGISTERED,
                created_at=datetime(2026, 8, 6, 12, 15),
            ),
            PatientResponse(
                patient_id="PAT-007",
                first_name="Emily",
                last_name="Watson",
                patient_name="Emily Watson",
                date_of_birth=date(1992, 3, 18),
                gender="Female",
                phone="+1-555-0107",
                address="150 Walnut Court, Springfield",
                status=PatientStatus.REGISTERED,
                created_at=datetime(2026, 8, 10, 10, 0),
            ),
            PatientResponse(
                patient_id="PAT-008",
                first_name="Alexander",
                last_name="Wright",
                patient_name="Alexander Wright",
                date_of_birth=date(1983, 12, 2),
                gender="Male",
                phone="+1-555-0108",
                address="882 Cypress Drive, Springfield",
                status=PatientStatus.REGISTERED,
                created_at=datetime(2026, 8, 12, 15, 30),
            ),
        ]
        for p in initial_patients:
            self._patients[p.patient_id] = p

    def reset(self):
        self._patients.clear()
        self._seed_patients()

    def get_all(self) -> List[PatientResponse]:
        return list(self._patients.values())

    def get_by_id(self, patient_id: str) -> Optional[PatientResponse]:
        return self._patients.get(patient_id)

    def get_by_phone(self, phone: str) -> Optional[PatientResponse]:
        clean = phone.strip()
        for p in self._patients.values():
            if p.phone == clean:
                return p
        return None

    def search(self, query: str) -> List[PatientResponse]:
        q = query.lower().strip()
        if not q:
            return self.get_all()
        return [
            p for p in self._patients.values()
            if q in p.patient_name.lower()
            or q in p.patient_id.lower()
            or q in p.phone
        ]

    def create(self, payload: PatientCreate) -> PatientResponse:
        seq = len(self._patients) + 1
        patient_id = f"PAT-{seq:03d}"
        full_name = f"{payload.first_name.strip()} {payload.last_name.strip()}"
        new_patient = PatientResponse(
            patient_id=patient_id,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            patient_name=full_name,
            date_of_birth=payload.date_of_birth,
            gender=payload.gender or "Other",
            phone=payload.phone.strip(),
            address=payload.address,
            status=PatientStatus.REGISTERED,
            created_at=datetime.utcnow(),
        )
        self._patients[patient_id] = new_patient
        return new_patient

    def update_status(
        self,
        patient_id: str,
        status: PatientStatus,
        arrival_time: Optional[datetime] = None,
    ) -> Optional[PatientResponse]:
        patient = self._patients.get(patient_id)
        if not patient:
            return None
        patient.status = status
        if arrival_time:
            patient.last_arrival_time = arrival_time
        return patient
