import uuid
from pydantic import BaseModel
from typing import Optional
from .domain import Claim, ClaimRepository

class ClaimDTO(BaseModel):
    id: Optional[str] = None
    policy_id: str
    description: str
    status: str = "PENDING"

class ClaimService:
    def __init__(self, repository: ClaimRepository):
        self.repository = repository

    def file_claim(self, dto: ClaimDTO) -> ClaimDTO:
        claim = Claim(
            id=str(uuid.uuid4()),
            policy_id=dto.policy_id,
            description=dto.description,
            status="PENDING"
        )
        self.repository.save(claim)
        return ClaimDTO(**claim.__dict__)

    def get_claim(self, claim_id: str) -> Optional[ClaimDTO]:
        claim = self.repository.get_by_id(claim_id)
        if claim:
            return ClaimDTO(**claim.__dict__)
        return None