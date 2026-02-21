from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional

@dataclass
class Policy:
    id: str
    customer_id: str
    policy_type: str
    coverage_amount: float

class PolicyRepository(ABC):
    @abstractmethod
    def save(self, policy: Policy) -> None: pass

    @abstractmethod
    def get_by_id(self, policy_id: str) -> Optional[Policy]: pass