from typing import Optional, Dict
from .domain import Claim, ClaimRepository

class InMemoryClaimRepository(ClaimRepository):
    def __init__(self):
        self._db: Dict[str, Claim] = {}

    def save(self, claim: Claim) -> None:
        self._db[claim.id] = claim

    def get_by_id(self, claim_id: str) -> Optional[Claim]:
        return self._db.get(claim_id)