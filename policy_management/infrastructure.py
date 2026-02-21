from typing import Optional, Dict
from .domain import Policy, PolicyRepository

class InMemoryPolicyRepository(PolicyRepository):
    def __init__(self):
        self._db: Dict[str, Policy] = {}

    def save(self, policy: Policy) -> None:
        self._db[policy.id] = policy

    def get_by_id(self, policy_id: str) -> Optional[Policy]:
        return self._db.get(policy_id)