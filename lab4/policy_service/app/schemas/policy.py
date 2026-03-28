from pydantic import BaseModel
from datetime import datetime


class PolicyCreate(BaseModel):
    customer_id: int
    policy_type: str


class PolicyResponse(BaseModel):
    id: int
    customer_id: int
    policy_type: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
