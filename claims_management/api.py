from fastapi import APIRouter, HTTPException
from .application import ClaimService, ClaimDTO
from .infrastructure import InMemoryClaimRepository

router = APIRouter(tags=["Claims"])
repo = InMemoryClaimRepository()
service = ClaimService(repo)

@router.post("/claims", response_model=ClaimDTO)
def create_claim(claim_data: ClaimDTO):
    return service.file_claim(claim_data)

@router.get("/claims/{claim_id}", response_model=ClaimDTO)
def get_claim(claim_id: str):
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim