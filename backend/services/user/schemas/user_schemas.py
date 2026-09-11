from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserCreateRequest(BaseModel):
    user_id: str
    full_name: str
    password: str
    role: str

class UserResponse(BaseModel):
    user_id: str
    full_name: str
    role: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
