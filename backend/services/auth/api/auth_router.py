from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Any
from pydantic import BaseModel

from backend.common.security import (
    verify_password,
    create_access_token,
    get_user_by_employee_id
)
from backend.common.audit_logger import log_action

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    employee_id: str

@router.post("/login", response_model=Token)
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    """
    Authenticate user and return a JWT access token.
    OAuth2PasswordRequestForm uses 'username' and 'password'. We map 'username' to 'employee_id'.
    """
    user = get_user_by_employee_id(form_data.username)
    if not user:
        log_action(form_data.username, "LOGIN_FAILED", {"reason": "User not found"}, request.client.host if request.client else None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user["hashed_password"]):
        log_action(user["employee_id"], "LOGIN_FAILED", {"reason": "Invalid password"}, request.client.host if request.client else None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    # Create access token
    access_token = create_access_token(data={"sub": user["employee_id"], "role": user["role"]})
    
    log_action(user["employee_id"], "LOGIN_SUCCESS", {"role": user["role"]}, request.client.host if request.client else None)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user["role"],
        "employee_id": user["employee_id"]
    }
