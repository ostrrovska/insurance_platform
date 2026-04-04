from pydantic import BaseModel, EmailStr
from datetime import datetime


class CustomerCreate(BaseModel):
    name: str
    email: EmailStr


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}
