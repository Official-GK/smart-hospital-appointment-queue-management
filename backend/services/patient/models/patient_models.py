import uuid
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from backend.services.patient.schemas.patient_schemas import (
    PatientCreate,
    PatientResponse,
    PatientStatus,
    PatientAuditRecord,
    PatientUpdateRequest,
)


class PatientRepository:
    """
    In-memory repository for patient demographics and status tracking.
    """

    def __init__(self):
        self._patients: Dict[str, PatientResponse] = {}
        self._audit_records: Dict[str, List[PatientAuditRecord]] = {}
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
        self._audit_records.clear()
        self._seed_patients()

    def get_all(self) -> List[PatientResponse]:
        return list(self._patients.values())

    def get_by_id(self, patient_id: str) -> Optional[PatientResponse]:
        return self._patients.get(patient_id)

    @staticmethod
    def normalize_phone(phone: str) -> str:
        if not phone:
            return ""
        return "".join(c for c in phone if c.isdigit())

    def get_by_phone(self, phone: str) -> Optional[PatientResponse]:
        target_clean = phone.strip()
        target_digits = self.normalize_phone(phone)
        for p in self._patients.values():
            if p.phone.strip() == target_clean:
                return p
            if target_digits and len(target_digits) >= 7 and self.normalize_phone(p.phone) == target_digits:
                return p
        return None

    def check_duplicate(
        self,
        phone: Optional[str] = None,
        identifier: Optional[str] = None,
    ) -> Optional[Tuple[PatientResponse, str]]:
        """
        Checks for duplicate registration based on identifier or contact number.
        Returns (existing_patient, matched_field) if duplicate found, else None.
        """
        if identifier and identifier.strip():
            clean_id = identifier.strip().upper()
            existing = self.get_by_id(clean_id)
            if existing:
                return existing, "identifier"

        if phone and phone.strip():
            existing = self.get_by_phone(phone)
            if existing:
                return existing, "contact_number"

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
        # Auto-generate unique Patient ID with collision avoidance
        max_seq = 0
        for pid in self._patients.keys():
            if pid.startswith("PAT-"):
                suffix = pid[4:]
                if suffix.isdigit():
                    max_seq = max(max_seq, int(suffix))
        next_seq = max_seq + 1
        patient_id = f"PAT-{next_seq:03d}"

        first_name = (payload.first_name or "").strip()
        last_name = (payload.last_name or "").strip()
        full_name = f"{first_name} {last_name}".strip() if last_name else first_name

        # Calculate age if date_of_birth is present and age is not
        age = payload.age
        dob = payload.date_of_birth
        today = date.today()
        if age is None and dob:
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        elif age is not None and dob is None:
            dob = date(today.year - age, 1, 1)

        new_patient = PatientResponse(
            patient_id=patient_id,
            first_name=first_name,
            last_name=last_name,
            patient_name=full_name,
            date_of_birth=dob,
            age=age,
            gender=payload.gender or "Other",
            phone=payload.phone.strip() if payload.phone else "",
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

    def update_patient(
        self,
        patient_id: str,
        payload: PatientUpdateRequest,
    ) -> Tuple[Optional[PatientResponse], List[PatientAuditRecord]]:
        patient = self._patients.get(patient_id)
        if not patient:
            return None, []

        now = datetime.utcnow()
        audits: List[PatientAuditRecord] = []
        changed_by = payload.updated_by or "Authorized Staff"

        if payload.first_name is not None and payload.first_name.strip() != patient.first_name:
            audits.append(
                PatientAuditRecord(
                    audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                    patient_id=patient_id,
                    timestamp=now,
                    changed_by=changed_by,
                    field_name="first_name",
                    old_value=patient.first_name,
                    new_value=payload.first_name.strip(),
                    notes=payload.notes,
                )
            )
            patient.first_name = payload.first_name.strip()
            patient.patient_name = f"{patient.first_name} {patient.last_name}"

        if payload.last_name is not None and payload.last_name.strip() != patient.last_name:
            audits.append(
                PatientAuditRecord(
                    audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                    patient_id=patient_id,
                    timestamp=now,
                    changed_by=changed_by,
                    field_name="last_name",
                    old_value=patient.last_name,
                    new_value=payload.last_name.strip(),
                    notes=payload.notes,
                )
            )
            patient.last_name = payload.last_name.strip()
            patient.patient_name = f"{patient.first_name} {patient.last_name}"

        if payload.phone is not None and payload.phone.strip() != patient.phone:
            audits.append(
                PatientAuditRecord(
                    audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                    patient_id=patient_id,
                    timestamp=now,
                    changed_by=changed_by,
                    field_name="phone",
                    old_value=patient.phone,
                    new_value=payload.phone.strip(),
                    notes=payload.notes,
                )
            )
            patient.phone = payload.phone.strip()

        if payload.address is not None and payload.address.strip() != (patient.address or ""):
            audits.append(
                PatientAuditRecord(
                    audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                    patient_id=patient_id,
                    timestamp=now,
                    changed_by=changed_by,
                    field_name="address",
                    old_value=patient.address,
                    new_value=payload.address.strip(),
                    notes=payload.notes,
                )
            )
            patient.address = payload.address.strip()

        if payload.gender is not None and payload.gender != patient.gender:
            audits.append(
                PatientAuditRecord(
                    audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                    patient_id=patient_id,
                    timestamp=now,
                    changed_by=changed_by,
                    field_name="gender",
                    old_value=patient.gender,
                    new_value=payload.gender,
                    notes=payload.notes,
                )
            )
            patient.gender = payload.gender

        if payload.date_of_birth is not None and payload.date_of_birth != patient.date_of_birth:
            audits.append(
                PatientAuditRecord(
                    audit_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                    patient_id=patient_id,
                    timestamp=now,
                    changed_by=changed_by,
                    field_name="date_of_birth",
                    old_value=patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                    new_value=payload.date_of_birth.isoformat(),
                    notes=payload.notes,
                )
            )
            patient.date_of_birth = payload.date_of_birth

        if audits:
            if patient_id not in self._audit_records:
                self._audit_records[patient_id] = []
            self._audit_records[patient_id].extend(audits)

        return patient, audits

    def get_audit_trail(self, patient_id: str) -> List[PatientAuditRecord]:
        return list(self._audit_records.get(patient_id, []))

