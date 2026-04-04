from pydantic import BaseModel
from datetime import datetime


class PaymentCreate(BaseModel):
    policy_id: int
    customer_id: int
    amount: float
    # Set to True to simulate a payment processing failure.
    # The saga orchestrator will then trigger compensation (cancel the policy).
    simulate_failure: bool = False


class PaymentResponse(BaseModel):
    id: int
    policy_id: int
    customer_id: int
    amount: float
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
