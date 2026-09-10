import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.database.connection import get_cursor

logger = logging.getLogger(__name__)

CREATE_TOKENS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tokens (
    token_id VARCHAR(50) PRIMARY KEY,
    token_number VARCHAR(50) NOT NULL,
    appointment_id VARCHAR(50),
    patient_id VARCHAR(50) NOT NULL,
    patient_name VARCHAR(100),
    doctor_id VARCHAR(50) NOT NULL,
    doctor_name VARCHAR(100),
    department_id VARCHAR(50) NOT NULL,
    department_name VARCHAR(100),
    priority VARCHAR(20) DEFAULT 'Normal',
    status VARCHAR(30) DEFAULT 'Waiting',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    queue_entry_time TIMESTAMP WITH TIME ZONE,
    called_time TIMESTAMP WITH TIME ZONE,
    consultation_start_time TIMESTAMP WITH TIME ZONE,
    consultation_end_time TIMESTAMP WITH TIME ZONE,
    estimated_wait_minutes INTEGER DEFAULT 15
);
CREATE INDEX IF NOT EXISTS idx_tokens_appointment_id ON tokens(appointment_id);
CREATE INDEX IF NOT EXISTS idx_tokens_patient_id ON tokens(patient_id);
CREATE INDEX IF NOT EXISTS idx_tokens_status ON tokens(status);
"""


def init_tokens_table() -> bool:
    """
    Ensures the tokens table and indices exist in PostgreSQL.
    Safely handles DB connection/execution errors.
    """
    try:
        with get_cursor(commit=True) as cur:
            if cur is None:
                return False
            cur.execute(CREATE_TOKENS_TABLE_SQL)
            return True
    except Exception as e:
        logger.warning(f"[Database] Could not initialize tokens table: {e}")
        return False


def fetch_token_by_appointment(appointment_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a token associated with a given appointment_id from PostgreSQL.
    Adheres to TECHNICAL_CONTRACTS.md Section 7 fields:
    token_id, token_number, patient_id, doctor_id, department_id, priority, status, created_at.
    
    Wrapped in try...except to gracefully handle database unavailability.
    """
    if not appointment_id:
        return None
    try:
        with get_cursor() as cur:
            if cur is None:
                return None
            query = """
                SELECT 
                    token_id,
                    token_number,
                    appointment_id,
                    patient_id,
                    patient_name,
                    doctor_id,
                    doctor_name,
                    department_id,
                    department_name,
                    priority,
                    status,
                    created_at,
                    queue_entry_time,
                    called_time,
                    consultation_start_time,
                    consultation_end_time,
                    estimated_wait_minutes
                FROM tokens
                WHERE appointment_id = %s
                ORDER BY created_at DESC
                LIMIT 1;
            """
            cur.execute(query, (appointment_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        logger.warning(f"[Database] Failed to fetch token for appointment '{appointment_id}': {e}")
        return None


def fetch_tokens_by_appointments(appointment_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Batch fetch tokens for a list of appointment_ids from PostgreSQL.
    Returns a dictionary mapping appointment_id -> token dict.
    
    Wrapped in try...except to gracefully handle database unavailability.
    """
    if not appointment_ids:
        return {}
    try:
        with get_cursor() as cur:
            if cur is None:
                return {}
            query = """
                SELECT 
                    token_id,
                    token_number,
                    appointment_id,
                    patient_id,
                    patient_name,
                    doctor_id,
                    doctor_name,
                    department_id,
                    department_name,
                    priority,
                    status,
                    created_at,
                    queue_entry_time,
                    called_time,
                    consultation_start_time,
                    consultation_end_time,
                    estimated_wait_minutes
                FROM tokens
                WHERE appointment_id = ANY(%s)
                ORDER BY created_at ASC;
            """
            cur.execute(query, (appointment_ids,))
            rows = cur.fetchall()
            tokens_map = {}
            for row in rows:
                tokens_map[row["appointment_id"]] = dict(row)
            return tokens_map
    except Exception as e:
        logger.warning(f"[Database] Failed to batch fetch tokens for appointments: {e}")
        return {}


def fetch_token_by_id(token_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a token directly by its token_id (e.g. 'TOK-101') from PostgreSQL.
    
    Wrapped in try...except to gracefully handle database unavailability.
    """
    if not token_id:
        return None
    try:
        with get_cursor() as cur:
            if cur is None:
                return None
            query = """
                SELECT 
                    token_id,
                    token_number,
                    appointment_id,
                    patient_id,
                    patient_name,
                    doctor_id,
                    doctor_name,
                    department_id,
                    department_name,
                    priority,
                    status,
                    created_at,
                    queue_entry_time,
                    called_time,
                    consultation_start_time,
                    consultation_end_time,
                    estimated_wait_minutes
                FROM tokens
                WHERE token_id = %s
                LIMIT 1;
            """
            cur.execute(query, (token_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None
    except Exception as e:
        logger.warning(f"[Database] Failed to fetch token by token_id '{token_id}': {e}")
        return None


def fetch_tokens_by_patient(patient_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all tokens for a given patient_id from PostgreSQL.
    """
    if not patient_id:
        return []
    try:
        with get_cursor() as cur:
            if cur is None:
                return []
            query = """
                SELECT 
                    token_id,
                    token_number,
                    appointment_id,
                    patient_id,
                    patient_name,
                    doctor_id,
                    doctor_name,
                    department_id,
                    department_name,
                    priority,
                    status,
                    created_at,
                    queue_entry_time,
                    called_time,
                    consultation_start_time,
                    consultation_end_time,
                    estimated_wait_minutes
                FROM tokens
                WHERE patient_id = %s
                ORDER BY created_at DESC;
            """
            cur.execute(query, (patient_id,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"[Database] Failed to fetch tokens for patient '{patient_id}': {e}")
        return []


def fetch_live_queue_tokens(
    department_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch active tokens (Waiting, Called, In Consultation) from PostgreSQL.
    """
    try:
        with get_cursor() as cur:
            if cur is None:
                return []
            conditions = ["status IN ('Waiting', 'Called', 'In Consultation')"]
            params = []
            if department_id:
                conditions.append("department_id = %s")
                params.append(department_id)
            if doctor_id:
                conditions.append("doctor_id = %s")
                params.append(doctor_id)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT 
                    token_id,
                    token_number,
                    appointment_id,
                    patient_id,
                    patient_name,
                    doctor_id,
                    doctor_name,
                    department_id,
                    department_name,
                    priority,
                    status,
                    created_at,
                    queue_entry_time,
                    called_time,
                    consultation_start_time,
                    consultation_end_time,
                    estimated_wait_minutes
                FROM tokens
                WHERE {where_clause}
                ORDER BY 
                    CASE WHEN priority = 'Emergency' THEN 0 ELSE 1 END,
                    queue_entry_time ASC;
            """
            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"[Database] Failed to fetch live queue from PostgreSQL: {e}")
        return []


def save_token(token_data: Dict[str, Any]) -> bool:
    """
    Save or update a token in PostgreSQL tokens table.
    Upserts using ON CONFLICT (token_id).
    
    Wrapped in try...except to gracefully handle database unavailability.
    """
    if not token_data or "token_id" not in token_data:
        return False
    try:
        with get_cursor(commit=True) as cur:
            if cur is None:
                return False
            query = """
                INSERT INTO tokens (
                    token_id,
                    token_number,
                    appointment_id,
                    patient_id,
                    patient_name,
                    doctor_id,
                    doctor_name,
                    department_id,
                    department_name,
                    priority,
                    status,
                    created_at,
                    queue_entry_time,
                    called_time,
                    consultation_start_time,
                    consultation_end_time,
                    estimated_wait_minutes
                ) VALUES (
                    %(token_id)s,
                    %(token_number)s,
                    %(appointment_id)s,
                    %(patient_id)s,
                    %(patient_name)s,
                    %(doctor_id)s,
                    %(doctor_name)s,
                    %(department_id)s,
                    %(department_name)s,
                    %(priority)s,
                    %(status)s,
                    %(created_at)s,
                    %(queue_entry_time)s,
                    %(called_time)s,
                    %(consultation_start_time)s,
                    %(consultation_end_time)s,
                    %(estimated_wait_minutes)s
                )
                ON CONFLICT (token_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    priority = EXCLUDED.priority,
                    called_time = COALESCE(EXCLUDED.called_time, tokens.called_time),
                    consultation_start_time = COALESCE(EXCLUDED.consultation_start_time, tokens.consultation_start_time),
                    consultation_end_time = COALESCE(EXCLUDED.consultation_end_time, tokens.consultation_end_time),
                    estimated_wait_minutes = EXCLUDED.estimated_wait_minutes;
            """
            # Ensure timestamps default to utcnow if None
            payload = {
                "token_id": token_data.get("token_id"),
                "token_number": token_data.get("token_number"),
                "appointment_id": token_data.get("appointment_id"),
                "patient_id": token_data.get("patient_id"),
                "patient_name": token_data.get("patient_name", ""),
                "doctor_id": token_data.get("doctor_id"),
                "doctor_name": token_data.get("doctor_name", ""),
                "department_id": token_data.get("department_id"),
                "department_name": token_data.get("department_name", ""),
                "priority": token_data.get("priority", "Normal"),
                "status": token_data.get("status", "Waiting"),
                "created_at": token_data.get("created_at") or datetime.utcnow(),
                "queue_entry_time": token_data.get("queue_entry_time") or datetime.utcnow(),
                "called_time": token_data.get("called_time"),
                "consultation_start_time": token_data.get("consultation_start_time"),
                "consultation_end_time": token_data.get("consultation_end_time"),
                "estimated_wait_minutes": token_data.get("estimated_wait_minutes", 15),
            }
            cur.execute(query, payload)
            return True
    except Exception as e:
        logger.warning(f"[Database] Failed to save token '{token_data.get('token_id')}' to PostgreSQL: {e}")
        return False
