from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional

@dataclass
class Claim:
    id: str
    policy_id: str
    description: str
    status: str

class ClaimRepository(ABC):
    @abstractmethod
    def save(self, claim: Claim) -> None: pass

    @abstractmethod
    def get_by_id(self, claim_id: str) -> Optional[Claim]: pass