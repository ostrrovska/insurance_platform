from fastapi import APIRouter, HTTPException
from .application import PolicyService, PolicyDTO
from .infrastructure import InMemoryPolicyRepository
from core.schemas import ErrorResponse
from customer_management.api import service as customer_service

router = APIRouter(tags=["Policies"])
repo = InMemoryPolicyRepository()
service = PolicyService(repo)


@router.post(
    "/policies",
    response_model=PolicyDTO,
    responses={
        400: {"model": ErrorResponse, "description": "Validation Error"},
        404: {"model": ErrorResponse, "description": "Customer not found"}  # Додаємо документацію для 404
    }
)
def create_policy(policy_data: PolicyDTO):
    customer = customer_service.get_customer(policy_data.customer_id)
    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot create policy: Customer with ID '{policy_data.customer_id}' does not exist"
        )
    return service.issue_policy(policy_data)


@router.get(
    "/policies/{policy_id}",
    response_model=PolicyDTO,
    responses={
        404: {"model": ErrorResponse, "description": "Policy not found"}
    }
)
def get_policy(policy_id: str):
    policy = service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy