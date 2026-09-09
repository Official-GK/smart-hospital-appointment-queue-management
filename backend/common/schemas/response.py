from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None
    error: Optional[Any] = None

    @classmethod
    def ok(cls, data: Optional[T] = None, message: str = "Operation completed successfully") -> "APIResponse[T]":
        return cls(success=True, message=message, data=data, error=None)

    @classmethod
    def fail(cls, message: str = "Request failed", error: Optional[Any] = None) -> "APIResponse[T]":
        return cls(success=False, message=message, data=None, error=error or {})
