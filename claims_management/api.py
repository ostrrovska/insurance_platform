from fastapi import APIRouter, HTTPException
from .application import ClaimService, ClaimDTO
from .infrastructure import InMemoryClaimRepository
from core.schemas import ErrorResponse

router = APIRouter(tags=["Claims"])
repo = InMemoryClaimRepository()
service = ClaimService(repo)

@router.post(
    "/claims",
    response_model=ClaimDTO,
    responses={
        400: {"model": ErrorResponse, "description": "Validation Error"}
    }
)
def create_claim(claim_data: ClaimDTO):
    return service.file_claim(claim_data)

@router.get(
    "/claims/{claim_id}",
    response_model=ClaimDTO,
    responses={
        404: {"model": ErrorResponse, "description": "Claim not found"}
    }
)
def get_claim(claim_id: str):
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim