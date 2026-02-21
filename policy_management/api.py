from fastapi import APIRouter, HTTPException
from .application import PolicyService, PolicyDTO
from .infrastructure import InMemoryPolicyRepository

router = APIRouter(tags=["Policies"])
repo = InMemoryPolicyRepository()
service = PolicyService(repo)

@router.post("/policies", response_model=PolicyDTO)
def create_policy(policy_data: PolicyDTO):
    return service.issue_policy(policy_data)

@router.get("/policies/{policy_id}", response_model=PolicyDTO)
def get_policy(policy_id: str):
    policy = service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy