"""
Patient database persistence module adhering to TECHNICAL_CONTRACTS.md Section 7.
Provides PostgreSQL storage, unique ID auto-generation, duplicate detection,
patient profile access, and audit trail tracking with in-memory fallback.
"""

import logging
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.database.connection import get_cursor
from backend.database.demo_data import DEMO_PATIENTS

logger = logging.getLogger(__name__)

CREATE_PATIENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS patients (
    patient_id VARCHAR(50) PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    patient_name VARCHAR(200) NOT NULL,
    date_of_birth DATE,
    age INTEGER,
    gender VARCHAR(20) DEFAULT 'Other',
    phone VARCHAR(50) NOT NULL,
    address TEXT,
    status VARCHAR(30) DEFAULT 'Registered',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_arrival_time TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone);
CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(patient_name);
CREATE INDEX IF NOT EXISTS idx_patients_status ON patients(status);

CREATE TABLE IF NOT EXISTS patient_audits (
    audit_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(100) NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_patient_audits_patient_id ON patient_audits(patient_id);
"""

# In-memory mirror for resilient fallback
_in_memory_patients: Dict[str, Dict[str, Any]] = {}
_in_memory_audits: Dict[str, List[Dict[str, Any]]] = {}


def normalize_phone(phone: Optional[str]) -> str:
    """Extract numeric digits from phone string for duplicate verification."""
    if not phone:
        return ""
    return "".join(c for c in phone if c.isdigit())


def init_patients_table() -> bool:
    """
    Ensure the patients and patient_audits tables exist in PostgreSQL and seed initial demo patients.
    """
    # Seed in-memory mirror first
    if not _in_memory_patients:
        for p in DEMO_PATIENTS:
            _in_memory_patients[p["patient_id"]] = dict(p)

    try:
        with get_cursor(commit=True) as cur:
            if cur is None:
                logger.info("[PatientDB] PostgreSQL not connected, using in-memory store.")
                return False

            cur.execute(CREATE_PATIENTS_TABLE_SQL)

            # Check if seed records exist
            cur.execute("SELECT COUNT(*) AS count FROM patients;")
            row = cur.fetchone()
            count = row["count"] if row else 0

            if count == 0:
                logger.info("[PatientDB] Seeding default patients into PostgreSQL...")
                insert_sql = """
                INSERT INTO patients (
                    patient_id, first_name, last_name, patient_name,
                    date_of_birth, age, gender, phone, address, status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (patient_id) DO NOTHING;
                """
                for p in DEMO_PATIENTS:
                    cur.execute(
                        insert_sql,
                        (
                            p["patient_id"],
                            p["first_name"],
                            p["last_name"],
                            p["patient_name"],
                            p.get("date_of_birth"),
                            p.get("age"),
                            p.get("gender", "Other"),
                            p["phone"],
                            p.get("address"),
                            p.get("status", "Registered"),
                        ),
                    )
                logger.info(f"[PatientDB] Successfully seeded {len(DEMO_PATIENTS)} default patients.")
            return True
    except Exception as e:
        logger.warning(f"[PatientDB] Could not initialize patients table in DB: {e}")
        return False


def reset_patients_db() -> bool:
    """
    Resets patients and audits to default seed state in DB and memory.
    """
    _in_memory_patients.clear()
    _in_memory_audits.clear()
    for p in DEMO_PATIENTS:
        _in_memory_patients[p["patient_id"]] = dict(p)

    try:
        with get_cursor(commit=True) as cur:
            if cur is not None:
                cur.execute("DELETE FROM patient_audits;")
                cur.execute("DELETE FROM patients;")
                insert_sql = """
                INSERT INTO patients (
                    patient_id, first_name, last_name, patient_name,
                    date_of_birth, age, gender, phone, address, status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (patient_id) DO NOTHING;
                """
                for p in DEMO_PATIENTS:
                    cur.execute(
                        insert_sql,
                        (
                            p["patient_id"],
                            p["first_name"],
                            p["last_name"],
                            p["patient_name"],
                            p.get("date_of_birth"),
                            p.get("age"),
                            p.get("gender", "Other"),
                            p["phone"],
                            p.get("address"),
                            p.get("status", "Registered"),
                        ),
                    )
                return True
    except Exception as e:
        logger.warning(f"[PatientDB] Could not reset DB: {e}")
    return False


def generate_next_patient_id() -> str:
    """
    Generate next unique Patient ID (PAT-XXX) by scanning existing IDs in DB and memory.
    """
    max_num = 0

    # 1. Query PostgreSQL if available
    try:
        with get_cursor() as cur:
            if cur is not None:
                cur.execute("SELECT patient_id FROM patients WHERE patient_id LIKE 'PAT-%';")
                rows = cur.fetchall()
                for r in rows:
                    pid = r["patient_id"]
                    suffix = pid[4:]
                    if suffix.isdigit():
                        max_num = max(max_num, int(suffix))
    except Exception as e:
        logger.debug(f"[PatientDB] Error querying max patient ID: {e}")

    # 2. Check in-memory mirror
    for pid in _in_memory_patients.keys():
        if pid.startswith("PAT-"):
            suffix = pid[4:]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))

    return f"PAT-{max_num + 1:03d}"


def fetch_patient_by_id(patient_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve patient record by unique Patient ID."""
    if not patient_id:
        return None

    try:
        with get_cursor() as cur:
            if cur is not None:
                cur.execute("SELECT * FROM patients WHERE patient_id = %s;", (patient_id,))
                row = cur.fetchone()
                if row:
                    return dict(row)
    except Exception as e:
        logger.debug(f"[PatientDB] Error fetching patient by ID: {e}")

    return _in_memory_patients.get(patient_id)


def fetch_patient_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve existing patient by phone number using exact or normalized digit matching.
    """
    if not phone:
        return None
    clean = phone.strip()
    digits = normalize_phone(phone)

    try:
        with get_cursor() as cur:
            if cur is not None:
                # Try exact match first
                cur.execute("SELECT * FROM patients WHERE phone = %s;", (clean,))
                row = cur.fetchone()
                if row:
                    return dict(row)

                # Try normalized match if digits length >= 7
                if len(digits) >= 7:
                    cur.execute("SELECT * FROM patients;")
                    all_rows = cur.fetchall()
                    for r in all_rows:
                        if normalize_phone(r.get("phone")) == digits:
                            return dict(r)
    except Exception as e:
        logger.debug(f"[PatientDB] Error fetching patient by phone: {e}")

    # In-memory search
    for p in _in_memory_patients.values():
        if p.get("phone", "").strip() == clean:
            return p
        if len(digits) >= 7 and normalize_phone(p.get("phone")) == digits:
            return p

    return None


def fetch_all_patients() -> List[Dict[str, Any]]:
    """Retrieve all patient records ordered by patient_id."""
    try:
        with get_cursor() as cur:
            if cur is not None:
                cur.execute("SELECT * FROM patients ORDER BY patient_id ASC;")
                rows = cur.fetchall()
                if rows:
                    return [dict(r) for r in rows]
    except Exception as e:
        logger.debug(f"[PatientDB] Error fetching all patients: {e}")

    return list(_in_memory_patients.values())


def search_patients_db(query: str) -> List[Dict[str, Any]]:
    """
    Search patient records by name, ID, or phone number.
    """
    q = query.strip()
    if not q:
        return fetch_all_patients()

    try:
        with get_cursor() as cur:
            if cur is not None:
                sql = """
                SELECT * FROM patients
                WHERE patient_id ILIKE %s
                   OR patient_name ILIKE %s
                   OR phone ILIKE %s
                ORDER BY patient_id ASC;
                """
                term = f"%{q}%"
                cur.execute(sql, (term, term, term))
                rows = cur.fetchall()
                if rows:
                    return [dict(r) for r in rows]
    except Exception as e:
        logger.debug(f"[PatientDB] Error searching patients: {e}")

    q_lower = q.lower()
    return [
        p for p in _in_memory_patients.values()
        if q_lower in p.get("patient_name", "").lower()
        or q_lower in p.get("patient_id", "").lower()
        or q_lower in p.get("phone", "").lower()
    ]


def register_patient_record(
    patient_data: Dict[str, Any],
    reuse_existing: bool = True,
) -> Tuple[Dict[str, Any], bool]:
    """
    Register a patient record in the database.
    - If patient already exists (by phone or identifier) and reuse_existing=True:
      Returns (existing_record, False). Same patient does NOT receive a new ID.
    - If new patient:
      Generates new unique Patient ID, saves to database and in-memory store,
      and returns (new_record, True).
    """
    phone = patient_data.get("phone") or patient_data.get("contact_number")
    identifier = patient_data.get("identifier") or patient_data.get("patient_id")

    # 1. Check duplicate / existing patient
    existing = None
    if identifier:
        existing = fetch_patient_by_id(identifier)
    if not existing and phone:
        existing = fetch_patient_by_phone(phone)

    if existing and reuse_existing:
        # Same patient does not require a new ID
        logger.info(f"[PatientDB] Patient already registered with ID '{existing['patient_id']}'. Reusing existing record.")
        return existing, False

    # 2. Generate new unique Patient ID
    patient_id = generate_next_patient_id()

    first_name = (patient_data.get("first_name") or "").strip()
    last_name = (patient_data.get("last_name") or "").strip()
    if not first_name and patient_data.get("name"):
        parts = patient_data["name"].strip().split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

    full_name = f"{first_name} {last_name}".strip() if last_name else first_name
    dob = patient_data.get("date_of_birth")
    age = patient_data.get("age")
    today = date.today()

    if age is None and dob:
        if isinstance(dob, str):
            dob = date.fromisoformat(dob)
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    elif age is not None and dob is None:
        dob = date(today.year - age, 1, 1)

    now = datetime.utcnow()
    record = {
        "patient_id": patient_id,
        "first_name": first_name,
        "last_name": last_name,
        "patient_name": full_name,
        "date_of_birth": dob,
        "age": age,
        "gender": patient_data.get("gender") or "Other",
        "phone": phone.strip() if phone else "",
        "address": patient_data.get("address"),
        "status": patient_data.get("status") or "Registered",
        "created_at": now,
        "last_arrival_time": None,
    }

    # 3. Persist to PostgreSQL
    try:
        with get_cursor(commit=True) as cur:
            if cur is not None:
                insert_sql = """
                INSERT INTO patients (
                    patient_id, first_name, last_name, patient_name,
                    date_of_birth, age, gender, phone, address, status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """
                cur.execute(
                    insert_sql,
                    (
                        record["patient_id"],
                        record["first_name"],
                        record["last_name"],
                        record["patient_name"],
                        record["date_of_birth"],
                        record["age"],
                        record["gender"],
                        record["phone"],
                        record["address"],
                        record["status"],
                        record["created_at"],
                    ),
                )
    except Exception as e:
        logger.warning(f"[PatientDB] Could not insert patient into PostgreSQL: {e}")

    # 4. Mirror in memory
    _in_memory_patients[patient_id] = record
    return record, True


def update_patient_status_db(
    patient_id: str,
    status: str,
    arrival_time: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """Update patient status and arrival timestamp."""
    patient = fetch_patient_by_id(patient_id)
    if not patient:
        return None

    patient["status"] = status
    if arrival_time:
        patient["last_arrival_time"] = arrival_time

    try:
        with get_cursor(commit=True) as cur:
            if cur is not None:
                if arrival_time:
                    cur.execute(
                        "UPDATE patients SET status = %s, last_arrival_time = %s WHERE patient_id = %s;",
                        (status, arrival_time, patient_id),
                    )
                else:
                    cur.execute(
                        "UPDATE patients SET status = %s WHERE patient_id = %s;",
                        (status, patient_id),
                    )
    except Exception as e:
        logger.warning(f"[PatientDB] Could not update patient status in DB: {e}")

    _in_memory_patients[patient_id] = patient
    return patient


def save_patient_audit_db(audit_record: Dict[str, Any]) -> bool:
    """Save demographic audit record in PostgreSQL and in-memory log."""
    pid = audit_record.get("patient_id")
    if not pid:
        return False

    audit_id = audit_record.get("audit_id") or f"AUD-{uuid.uuid4().hex[:8].upper()}"
    audit_record["audit_id"] = audit_id

    try:
        with get_cursor(commit=True) as cur:
            if cur is not None:
                sql = """
                INSERT INTO patient_audits (
                    audit_id, patient_id, timestamp, changed_by,
                    field_name, old_value, new_value, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """
                cur.execute(
                    sql,
                    (
                        audit_id,
                        pid,
                        audit_record.get("timestamp") or datetime.utcnow(),
                        audit_record.get("changed_by", "Authorized Staff"),
                        audit_record.get("field_name"),
                        audit_record.get("old_value"),
                        audit_record.get("new_value"),
                        audit_record.get("notes"),
                    ),
                )
    except Exception as e:
        logger.debug(f"[PatientDB] Could not insert audit in PostgreSQL: {e}")

    if pid not in _in_memory_audits:
        _in_memory_audits[pid] = []
    _in_memory_audits[pid].append(audit_record)
    return True


def fetch_patient_audits_db(patient_id: str) -> List[Dict[str, Any]]:
    """Retrieve all audit records for a patient."""
    try:
        with get_cursor() as cur:
            if cur is not None:
                cur.execute(
                    "SELECT * FROM patient_audits WHERE patient_id = %s ORDER BY timestamp DESC;",
                    (patient_id,),
                )
                rows = cur.fetchall()
                if rows:
                    return [dict(r) for r in rows]
    except Exception as e:
        logger.debug(f"[PatientDB] Error fetching audits from DB: {e}")

    return _in_memory_audits.get(patient_id, [])


# Initialize tables and seed on module load
init_patients_table()
