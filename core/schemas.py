from pydantic import BaseModel, Field
from typing import Optional, Any

class ErrorResponse(BaseModel):
    error_code: int = Field(..., example=404)
    description: str = Field(..., example="Not found")
    timestamp: str = Field(..., example="2026-02-28T12:44:12.695876+00:00")
    details: Optional[Any] = None