"""
Database module for PostgreSQL connections and token operations.
Provides resilient data fetching adhering to TECHNICAL_CONTRACTS.md.
"""

from backend.database.connection import check_connection, get_cursor, get_db_connection
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
    "fetch_token_by_appointment",
    "fetch_tokens_by_appointments",
    "fetch_token_by_id",
    "fetch_tokens_by_patient",
    "fetch_live_queue_tokens",
    "save_token",
    "DEPARTMENTS",
    "DOCTORS",
    "DEFAULT_SLOTS",
    "get_demo_appointments",
    "get_demo_released_slots",
]
