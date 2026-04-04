from pydantic import BaseModel
from datetime import datetime
from typing import Literal


class PolicyCreate(BaseModel):
    customer_id: int
    policy_type: str
    coverage_amount: float = 0.0
    premium_amount: float = 0.0
    # Optional: caller (saga orchestrator) can specify initial status.
    # Defaults to PENDING so the saga can activate it after payment.
    status: str = "PENDING"


class PolicyStatusUpdate(BaseModel):
    """Used by the saga orchestrator to change a policy's status."""
    status: Literal["PENDING", "ACTIVE", "CANCELLED"]


class PolicyResponse(BaseModel):
    id: int
    customer_id: int
    policy_type: str
    coverage_amount: float
    premium_amount: float
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
