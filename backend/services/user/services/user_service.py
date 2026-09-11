from typing import List
from psycopg2.extras import RealDictCursor
from backend.database.connection import get_cursor
from backend.common.security import get_password_hash
from backend.services.user.schemas.user_schemas import UserCreateRequest
import uuid
import logging

logger = logging.getLogger(__name__)

class UserService:
    def get_all_users(self) -> List[dict]:
        with get_cursor() as cur:
            cur.execute("""
                SELECT user_id, employee_id as user_id, role, created_at, 'User' as full_name 
                FROM users 
                WHERE is_active = TRUE 
                ORDER BY created_at DESC;
            """)
            rows = cur.fetchall()
            # Map employee_id to user_id for the frontend response, and provide a dummy full_name if missing
            results = []
            for r in rows:
                row_dict = dict(r)
                row_dict["full_name"] = row_dict["user_id"] # Use employee_id as full_name for now
                results.append(row_dict)
            return results

    def create_user(self, payload: UserCreateRequest) -> dict:
        hashed_pw = get_password_hash(payload.password)
        new_id = str(uuid.uuid4())
        with get_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO users (user_id, employee_id, role, hashed_password, is_active)
                VALUES (%s, %s, %s, %s, TRUE)
                RETURNING user_id, employee_id, role, created_at
            """, (new_id, payload.user_id, payload.role, hashed_pw))
            row = cur.fetchone()
            row_dict = dict(row)
            # Map employee_id to user_id for the response
            row_dict["full_name"] = payload.full_name
            row_dict["user_id"] = row_dict["employee_id"]
            return row_dict

    def delete_user(self, employee_id: str) -> bool:
        if employee_id == "ADMIN-001":
            raise ValueError("Cannot delete the root admin user")
            
        with get_cursor(commit=True) as cur:
            cur.execute("""
                DELETE FROM users
                WHERE employee_id = %s
                RETURNING employee_id;
            """, (employee_id,))
            row = cur.fetchone()
            return row is not None

user_service_instance = UserService()
