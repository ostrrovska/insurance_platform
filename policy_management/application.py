import uuid
from pydantic import BaseModel
from typing import Optional
from .domain import Policy, PolicyRepository

class PolicyDTO(BaseModel):
    id: Optional[str] = None
    customer_id: str
    policy_type: str
    coverage_amount: float

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