"""
PostgreSQL Database Setup & Seed Utility for Hospital System.
Creates the database (hospital_db), initializes the tokens table adhering
to TECHNICAL_CONTRACTS.md Section 7, and seeds test tokens.
"""

import os
import sys
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load local environment
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("setup_db")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "hospital_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", os.getenv("USER", "postgres"))
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")


def get_maintenance_connection():
    """
    Connect to default maintenance database 'postgres' to create 'hospital_db' if needed.
    Tries multiple common user configurations.
    """
    users_to_try = [
        (POSTGRES_USER, POSTGRES_PASSWORD),
        (os.getenv("USER"), ""),
        ("postgres", "postgres"),
        ("postgres", ""),
    ]

    for user, pwd in users_to_try:
        if not user:
            continue
        try:
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                dbname="postgres",
                user=user,
                password=pwd,
                connect_timeout=3,
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            logger.info(f"Connected to PostgreSQL maintenance DB using user '{user}'")
            return conn, user, pwd
        except Exception as e:
            continue

    logger.error("Could not connect to PostgreSQL. Ensure PostgreSQL is running on port 5432.")
    return None, None, None


def create_database_if_not_exists(conn, db_name):
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
    exists = cur.fetchone()
    if not exists:
        logger.info(f"Database '{db_name}' does not exist. Creating...")
        cur.execute(f'CREATE DATABASE "{db_name}";')
        logger.info(f"Database '{db_name}' created successfully.")
    else:
        logger.info(f"Database '{db_name}' already exists.")
    cur.close()


def setup_tokens_schema_and_seed(db_user, db_password):
    """
    Connect to hospital_db, create tokens table and insert configured tokens.
    """
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=db_user,
            password=db_password,
            connect_timeout=3,
        )
        conn.autocommit = True
        cur = conn.cursor()

        # Create table per TECHNICAL_CONTRACTS.md Section 7
        logger.info("Ensuring 'tokens' table exists...")
        create_table_sql = """
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
            queue_entry_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            called_time TIMESTAMP WITH TIME ZONE,
            consultation_start_time TIMESTAMP WITH TIME ZONE,
            consultation_end_time TIMESTAMP WITH TIME ZONE,
            estimated_wait_minutes INTEGER DEFAULT 15
        );
        CREATE INDEX IF NOT EXISTS idx_tokens_appointment_id ON tokens(appointment_id);
        CREATE INDEX IF NOT EXISTS idx_tokens_patient_id ON tokens(patient_id);
        CREATE INDEX IF NOT EXISTS idx_tokens_status ON tokens(status);
        """
        cur.execute(create_table_sql)
        logger.info("'tokens' table is ready.")

        cur.close()
        conn.close()
        logger.info("Database schema is ready. No demo tokens seeded (awaiting external configuration).")
        return True
    except Exception as e:
        logger.error(f"Failed to setup tokens table in hospital_db: {e}")
        return False


def main():
    logger.info("Starting PostgreSQL Database Setup...")
    conn, user, pwd = get_maintenance_connection()
    if not conn:
        sys.exit(1)

    create_database_if_not_exists(conn, POSTGRES_DB)
    conn.close()

    success = setup_tokens_schema_and_seed(user, pwd)
    if success:
        logger.info(f"SUCCESS: PostgreSQL is fully configured. User: '{user}', DB: '{POSTGRES_DB}'")
        # Update .env if user or password changed
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path, "w") as f:
                f.write(f"POSTGRES_HOST={POSTGRES_HOST}\n")
                f.write(f"POSTGRES_PORT={POSTGRES_PORT}\n")
                f.write(f"POSTGRES_DB={POSTGRES_DB}\n")
                f.write(f"POSTGRES_USER={user}\n")
                f.write(f"POSTGRES_PASSWORD={pwd}\n")
                f.write(f"DATABASE_URL=postgresql://{user}:{pwd}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}\n")
                f.write("POSTGRES_CONNECT_TIMEOUT=2\n")
            logger.info(f"Updated {env_path} with verified connection details.")


if __name__ == "__main__":
    main()
