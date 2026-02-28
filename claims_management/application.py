import uuid
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from .domain import Claim, ClaimRepository

class ClaimStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ClaimDTO(BaseModel):
    id: Optional[str] = None
    policy_id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=10, max_length=1000, description="Detailed claim description")
    status: ClaimStatus = Field(default=ClaimStatus.PENDING)

class ClaimService:
    def __init__(self, repository: ClaimRepository):
        self.repository = repository

    def file_claim(self, dto: ClaimDTO) -> ClaimDTO:
        claim = Claim(
            id=str(uuid.uuid4()),
            policy_id=dto.policy_id,
            description=dto.description,
            status=dto.status.value
        )
        self.repository.save(claim)
        return ClaimDTO(id=claim.id, policy_id=claim.policy_id, description=claim.description, status=ClaimStatus(claim.status))

    def get_claim(self, claim_id: str) -> Optional[ClaimDTO]:
        claim = self.repository.get_by_id(claim_id)
        if claim:
            return ClaimDTO(id=claim.id, policy_id=claim.policy_id, description=claim.description, status=ClaimStatus(claim.status))
        return None