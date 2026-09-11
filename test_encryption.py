import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.token_fetcher import save_token, fetch_live_queue_tokens
from backend.database.connection import get_cursor

# Create a mock token
token_data = {
    "token_id": "test-enc-token",
    "token_number": "T123",
    "appointment_id": "test-enc-appt",
    "patient_id": "P999",
    "patient_name": "John Doe Encrypted",
    "doctor_id": "D1",
    "doctor_name": "Dr. Smith",
    "department_id": "DEP1",
    "department_name": "Cardiology",
    "priority": "Normal",
    "status": "Waiting"
}

# Save token
res = save_token(token_data)
print(f"Saved: {res}")

# Fetch directly from DB
with get_cursor() as cur:
    cur.execute("SELECT patient_name FROM tokens WHERE token_id = 'test-enc-token'")
    row = cur.fetchone()
    print(f"Raw DB value: {row['patient_name']}")

# Fetch via token_fetcher
live = fetch_live_queue_tokens()
for token in live:
    if token["token_id"] == "test-enc-token":
        print(f"Decrypted API value: {token['patient_name']}")
