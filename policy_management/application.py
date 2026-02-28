import uuid
from pydantic import BaseModel, Field
from typing import Optional
from .domain import Policy, PolicyRepository

class PolicyDTO(BaseModel):
    id: Optional[str] = None
    customer_id: str = Field(..., min_length=1, description="Associated customer ID")
    policy_type: str = Field(..., min_length=3, max_length=100)
    coverage_amount: float = Field(..., gt=0, description="Coverage amount must be greater than 0")

class PolicyService:
    def __init__(self, repository: PolicyRepository):
        self.repository = repository

    def issue_policy(self, dto: PolicyDTO) -> PolicyDTO:
        policy = Policy(
            id=str(uuid.uuid4()),
            customer_id=dto.customer_id,
            policy_type=dto.policy_type,
            coverage_amount=dto.coverage_amount
        )
        self.repository.save(policy)
        return PolicyDTO(**policy.__dict__)

    def get_policy(self, policy_id: str) -> Optional[PolicyDTO]:
        policy = self.repository.get_by_id(policy_id)
        if policy:
            return PolicyDTO(**policy.__dict__)
        return None