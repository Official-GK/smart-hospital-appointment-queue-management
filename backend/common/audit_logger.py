import uuid
import json
from typing import Any, Dict
from datetime import datetime, timezone
import logging
from backend.database.connection import get_db_connection

logger = logging.getLogger(__name__)

def sanitize_audit_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strips sensitive information such as plain-text passwords and PII
    from the audit logs payload.
    """
    sanitized = {}
    for key, value in details.items():
        lower_key = key.lower()
        if "password" in lower_key or "secret" in lower_key or "token" in lower_key:
            sanitized[key] = "[REDACTED]"
        elif key in ["patient_name", "phone", "national_id", "address"]:
            # Further strip PII
            sanitized[key] = "[REDACTED_PII]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_audit_details(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_audit_details(item) if isinstance(item, dict) else item 
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized

def log_action(employee_id: str, action: str, details: Dict[str, Any], ip_address: str = None):
    """
    Writes an immutable audit log entry into the database.
    """
    log_id = str(uuid.uuid4())
    sanitized_details = sanitize_audit_details(details)
    
    conn = get_db_connection()
    if not conn:
        logger.error(f"Failed to connect to DB to write audit log: {action}")
        return
        
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_logs (log_id, employee_id, action, details, ip_address, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    log_id, 
                    employee_id, 
                    action, 
                    json.dumps(sanitized_details), 
                    ip_address, 
                    datetime.now(timezone.utc)
                )
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Error writing audit log {log_id}: {str(e)}")
        conn.rollback()
    finally:
        conn.close()
