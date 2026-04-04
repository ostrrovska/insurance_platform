"""
Policy Service API.

Lab5 additions over lab4:
  - PolicyCreate now accepts coverage_amount, premium_amount, and optional status.
  - PATCH /{id}/status  — Saga orchestrator activates or cancels a policy.

Lab6 addition:
  - GET /?customer_id={id} — filter policies by customer (used by API Gateway composition).

All status changes publish events to the outbox so the Notification
Service gets notified of the final outcome.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.policy import Policy
from app.outbox.writer import publish_event
from app.schemas.policy import PolicyCreate, PolicyResponse, PolicyStatusUpdate
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
    Create a new policy.

    When called by the saga orchestrator the initial status is PENDING.
    The orchestrator will call PATCH /{id}/status to set it to ACTIVE
    after the payment succeeds, or DELETE /{id} to cancel it if payment fails.
    """
    # Validate that the customer exists (synchronous HTTP call with retry)
    customer = await customer_client.get_customer(body.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {body.customer_id} not found")

    # Create the policy record
    policy = Policy(
        customer_id=body.customer_id,
        policy_type=body.policy_type,
        coverage_amount=body.coverage_amount,
        premium_amount=body.premium_amount,
        status=body.status,  # PENDING when called from saga
    )
    db.add(policy)
    await db.flush()  # assigns PK without committing

    # Atomically write a PolicyCreated outbox event in the same transaction
    await publish_event(
        db,
        event_type="PolicyCreated",
        exchange=EXCHANGE,
        routing_key="policies.created",
        payload={
            "policy_id": policy.id,
            "customer_id": policy.customer_id,
            "policy_type": policy.policy_type,
            "coverage_amount": policy.coverage_amount,
            "premium_amount": policy.premium_amount,
            "status": policy.status,
            "correlation_id": x_correlation_id,
        },
    )

    await db.commit()
    await db.refresh(policy)

    logger.info(
        "Created policy id=%d for customer_id=%d status=%s [correlation=%s]",
        policy.id, policy.customer_id, policy.status, x_correlation_id,
    )
    return policy


@router.patch("/{policy_id}/status", response_model=PolicyResponse)
async def update_policy_status(
    policy_id: int,
    body: PolicyStatusUpdate,
    db: AsyncSession = Depends(get_db),
    x_correlation_id: str | None = Header(default=None),
):
    """
    Update the status of an existing policy.

    Used by the saga orchestrator:
      - PENDING → ACTIVE  : payment confirmed, activate the policy.
      - PENDING → CANCELLED: compensation step, payment failed.
    Publishes a PolicyActivated or PolicyCancelled event to the outbox.
    """
    policy = await db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    old_status = policy.status
    policy.status = body.status
    policy.updated_at = datetime.now(timezone.utc)

    # Choose the right event type and routing key based on the new status
    if body.status == "ACTIVE":
        event_type = "PolicyActivated"
        routing_key = "policies.activated"
    elif body.status == "CANCELLED":
        event_type = "PolicyCancelled"
        routing_key = "policies.cancelled"
    else:
        event_type = "PolicyStatusChanged"
        routing_key = "policies.status_changed"

    # Publish event atomically with the status update
    await publish_event(
        db,
        event_type=event_type,
        exchange=EXCHANGE,
        routing_key=routing_key,
        payload={
            "policy_id": policy.id,
            "customer_id": policy.customer_id,
            "policy_type": policy.policy_type,
            "old_status": old_status,
            "new_status": body.status,
            "correlation_id": x_correlation_id,
        },
    )

    await db.commit()
    await db.refresh(policy)

    logger.info(
        "Policy id=%d status changed: %s → %s [correlation=%s]",
        policy_id, old_status, body.status, x_correlation_id,
    )
    return policy


@router.get("/", response_model=list[PolicyResponse])
async def list_policies(
    # Lab6: optional filter by customer_id — used by API Gateway composition endpoint
    customer_id: Optional[int] = Query(default=None, description="Filter by customer ID"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Policy).order_by(Policy.id)
    if customer_id is not None:
        stmt = stmt.where(Policy.customer_id == customer_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: int, db: AsyncSession = Depends(get_db)):
    policy = await db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy
