"""
Database module for PostgreSQL connections and token operations.
Provides resilient data fetching adhering to TECHNICAL_CONTRACTS.md.
"""

from backend.database.connection import check_connection, get_cursor, get_db_connection
from backend.database.patient_db import (
    fetch_all_patients,
    fetch_patient_audits_db,
    fetch_patient_by_id,
    fetch_patient_by_phone,
    generate_next_patient_id,
    init_patients_table,
    register_patient_record,
    save_patient_audit_db,
    search_patients_db,
    update_patient_status_db,
)
from backend.database.token_fetcher import (
    fetch_live_queue_tokens,
    fetch_token_by_appointment,
    fetch_token_by_id,
    fetch_tokens_by_appointments,
    fetch_tokens_by_patient,
    init_tokens_table,
    save_token,
)

from backend.database.demo_data import (
    DEFAULT_SLOTS,
    DEMO_PATIENTS,
    DEPARTMENTS,
    DOCTORS,
    get_demo_appointments,
    get_demo_released_slots,
)

__all__ = [
    "get_db_connection",
    "get_cursor",
    "check_connection",
    "init_tokens_table",
    "init_patients_table",
    "fetch_patient_by_id",
    "fetch_patient_by_phone",
    "fetch_all_patients",
    "search_patients_db",
    "generate_next_patient_id",
    "register_patient_record",
    "update_patient_status_db",
    "save_patient_audit_db",
    "fetch_patient_audits_db",
    "fetch_token_by_appointment",
    "fetch_tokens_by_appointments",
    "fetch_token_by_id",
    "fetch_tokens_by_patient",
    "fetch_live_queue_tokens",
    "save_token",
    "DEPARTMENTS",
    "DOCTORS",
    "DEMO_PATIENTS",
    "DEFAULT_SLOTS",
    "get_demo_appointments",
    "get_demo_released_slots",
]

