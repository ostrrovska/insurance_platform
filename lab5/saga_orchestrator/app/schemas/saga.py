import json
from pydantic import BaseModel
from datetime import datetime
from typing import Any


class PolicyPurchaseRequest(BaseModel):
    """
    Input for starting a Policy Purchase Saga.

    Set simulate_payment_failure=True to trigger the compensation path.
    This lets you demonstrate that when payment fails, the policy is
    automatically cancelled (compensating transaction).
    """
    customer_id: int
    policy_type: str
    coverage_amount: float
    premium_amount: float
    simulate_payment_failure: bool = False


class SagaResponse(BaseModel):
    id: str
    saga_type: str
    status: str
    customer_id: int
    policy_type: str
    coverage_amount: float
    premium_amount: float
    policy_id: int | None
    payment_id: int | None
    error: str | None
    steps_log: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_steps(cls, saga) -> "SagaResponse":
        """Deserialize steps_log from JSON string before returning."""
        data = {
            "id": saga.id,
            "saga_type": saga.saga_type,
            "status": saga.status,
            "customer_id": saga.customer_id,
            "policy_type": saga.policy_type,
            "coverage_amount": saga.coverage_amount,
            "premium_amount": saga.premium_amount,
            "policy_id": saga.policy_id,
            "payment_id": saga.payment_id,
            "error": saga.error,
            "steps_log": json.loads(saga.steps_log) if saga.steps_log else [],
            "created_at": saga.created_at,
            "updated_at": saga.updated_at,
        }
        return cls(**data)
