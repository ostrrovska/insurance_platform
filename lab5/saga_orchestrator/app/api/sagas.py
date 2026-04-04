"""
Saga Orchestrator API.

Endpoints:
  POST /sagas/policy-purchase  — Start a new Policy Purchase Saga
  GET  /sagas/                 — List all sagas (latest first)
  GET  /sagas/{saga_id}        — Get full saga details including step log
"""

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.saga import Saga
from app.schemas.saga import PolicyPurchaseRequest, SagaResponse
from app.services.policy_purchase_saga import run_policy_purchase_saga

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sagas", tags=["Sagas"])


@router.post(
    "/policy-purchase",
    response_model=SagaResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_policy_purchase_saga(
    body: PolicyPurchaseRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a Policy Purchase Saga.

    The saga record is created synchronously (you get the ID immediately),
    then execution continues in the background. Poll GET /sagas/{id} to
    follow progress.

    Set simulate_payment_failure=True to trigger the compensation path:
    the payment will intentionally fail and the saga will automatically
    cancel the PENDING policy (compensating transaction).

    Steps:
      1. Validate customer exists
      2. Create policy (status=PENDING)
      3. Process payment
      4. Activate policy (status=ACTIVE)
      → COMPLETED

    If step 3 fails → policy gets CANCELLED (compensating transaction).
    """
    # ── Create the saga record synchronously ─────────────────────────────
    # This ensures we always return a valid saga_id in the 202 response,
    # even before any steps have executed.
    saga_id = str(uuid.uuid4())
    saga = Saga(
        id=saga_id,
        saga_type="POLICY_PURCHASE",
        status="STARTED",
        customer_id=body.customer_id,
        policy_type=body.policy_type,
        coverage_amount=body.coverage_amount,
        premium_amount=body.premium_amount,
    )
    saga.append_step("STARTED", f"Saga initiated for customer_id={body.customer_id}")
    db.add(saga)
    await db.commit()
    await db.refresh(saga)

    # ── Launch saga execution as a background task ────────────────────────
    # The background task uses its own DB session (AsyncSessionLocal)
    # so it doesn't interfere with the request session.
    asyncio.create_task(
        run_policy_purchase_saga(
            saga_id=saga_id,
            customer_id=body.customer_id,
            policy_type=body.policy_type,
            coverage_amount=body.coverage_amount,
            premium_amount=body.premium_amount,
            simulate_payment_failure=body.simulate_payment_failure,
        )
    )

    logger.info(
        "Saga %s created and background task started (customer_id=%d simulate_failure=%s)",
        saga_id, body.customer_id, body.simulate_payment_failure,
    )
    return SagaResponse.from_orm_with_steps(saga)


@router.get("/{saga_id}", response_model=SagaResponse)
async def get_saga(saga_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get full saga details including the step-by-step execution log.

    Use this to:
      • Monitor saga progress in real time
      • Verify that compensation ran after a failed payment
      • See which resources (policy_id, payment_id) were created/rolled back
    """
    saga = await db.get(Saga, saga_id)
    if not saga:
        raise HTTPException(status_code=404, detail=f"Saga {saga_id} not found")
    return SagaResponse.from_orm_with_steps(saga)


@router.get("/", response_model=list[SagaResponse])
async def list_sagas(db: AsyncSession = Depends(get_db)):
    """List all sagas, most recent first."""
    result = await db.execute(select(Saga).order_by(Saga.created_at.desc()))
    sagas = result.scalars().all()
    return [SagaResponse.from_orm_with_steps(s) for s in sagas]
