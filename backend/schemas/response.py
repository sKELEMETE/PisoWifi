from typing import Any

from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: Any = None


class ApiError(BaseModel):
    success: bool = False
    message: str = ""
    errors: list[str] = Field(default_factory=list)
