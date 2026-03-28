import logging

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.policy import Policy
from app.outbox.writer import publish_event
from app.schemas.policy import PolicyCreate, PolicyResponse
from app.services.customer_client import customer_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/policies", tags=["Policies"])

EXCHANGE = "policies"


@router.post("/", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    body: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    x_correlation_id: str | None = Header(default=None),
):
    """
    1. Validates customer exists (synchronous HTTP call).
    2. Creates policy record.
    3. Atomically writes PolicyCreated event to Outbox.
    4. Relay publishes the event to RabbitMQ when broker is available.
    """
    # Synchronous validation
    customer = await customer_client.get_customer(body.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {body.customer_id} not found")

    # Business operation
    policy = Policy(customer_id=body.customer_id, policy_type=body.policy_type)
    db.add(policy)
    await db.flush()

    # Outbox event — same transaction!
    await publish_event(
        db,
        event_type="PolicyCreated",
        exchange=EXCHANGE,
        routing_key="policies.created",
        payload={
            "policy_id": policy.id,
            "customer_id": policy.customer_id,
            "policy_type": policy.policy_type,
            "status": policy.status,
            "correlation_id": x_correlation_id,
        },
    )

    await db.commit()
    await db.refresh(policy)

    logger.info(
        "Created policy id=%d for customer_id=%d [correlation=%s]",
        policy.id, policy.customer_id, x_correlation_id,
    )
    return policy


@router.get("/", response_model=list[PolicyResponse])
async def list_policies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Policy).order_by(Policy.id))
    return result.scalars().all()


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: int, db: AsyncSession = Depends(get_db)):
    policy = await db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy
