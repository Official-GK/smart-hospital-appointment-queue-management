from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from backend.common.security import RoleChecker, get_current_user
from backend.common.audit_logger import log_action
from backend.services.user.schemas.user_schemas import UserCreateRequest, UserResponse
from backend.services.user.services.user_service import user_service_instance

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

@router.get("", response_model=List[UserResponse], dependencies=[Depends(RoleChecker(["admin"]))])
def list_users():
    return user_service_instance.get_all_users()

@router.post("", response_model=UserResponse, dependencies=[Depends(RoleChecker(["admin"]))])
def create_user(payload: UserCreateRequest, req: Request, user: dict = Depends(get_current_user)):
    try:
        new_user = user_service_instance.create_user(payload)
        log_action(user["employee_id"], "CREATE_USER", {"new_user_id": payload.user_id}, req.client.host if req.client else None)
        return new_user
    except Exception as e:
        if "duplicate key value" in str(e):
            raise HTTPException(status_code=409, detail=f"User ID '{payload.user_id}' already exists.")
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{user_id}", dependencies=[Depends(RoleChecker(["admin"]))])
def delete_user(user_id: str, req: Request, user: dict = Depends(get_current_user)):
    try:
        success = user_service_instance.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        log_action(user["employee_id"], "DELETE_USER", {"deleted_user_id": user_id}, req.client.host if req.client else None)
        return {"message": f"User '{user_id}' deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
