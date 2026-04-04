"""
Payment Service API.

This service is responsible for charging the customer's premium.
It participates in the Policy Purchase Saga as Step 3.

Endpoints:
  POST /payments/           — Process a payment (Step 3 of the saga)
  POST /payments/{id}/refund — Refund a payment (Compensating transaction)
  GET  /payments/           — List all payments
  GET  /payments/{id}       — Get a single payment

The simulate_failure flag in PaymentCreate allows us to deliberately
fail a payment to demonstrate the saga's compensation mechanism.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def process_payment(body: PaymentCreate, db: AsyncSession = Depends(get_db)):
    """
    Process a premium payment for a policy.

    If simulate_failure is True, the payment is recorded with status=FAILED
    and HTTP 402 is returned — the saga orchestrator will catch this and
    execute the compensating transaction (cancel the policy).

    In a real system this would integrate with a payment gateway (Stripe, etc.).
    """
    if body.simulate_failure:
        # Record the failed attempt in the DB for audit purposes
        payment = Payment(
            policy_id=body.policy_id,
            customer_id=body.customer_id,
            amount=body.amount,
            status="FAILED",
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        logger.warning(
            "Payment FAILED (simulated) for policy_id=%d customer_id=%d amount=%.2f",
            body.policy_id, body.customer_id, body.amount,
        )
        # Return 402 Payment Required so the saga knows to compensate
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Payment failed (simulated). Payment record id={payment.id} saved with status=FAILED.",
        )

    # Happy path: record a successful payment
    payment = Payment(
        policy_id=body.policy_id,
        customer_id=body.customer_id,
        amount=body.amount,
        status="COMPLETED",
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    logger.info(
        "Payment COMPLETED id=%d policy_id=%d customer_id=%d amount=%.2f",
        payment.id, payment.policy_id, payment.customer_id, payment.amount,
    )
    return payment


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
async def refund_payment(payment_id: int, db: AsyncSession = Depends(get_db)):
    """
    Refund a previously completed payment.

    This is the COMPENSATING TRANSACTION for the payment step.
    Called by the saga orchestrator when a later step fails
    (e.g. policy activation failed after payment was already taken).

    In a real system this would call the payment gateway's refund API.
    """
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot refund payment with status={payment.status}. Only COMPLETED payments can be refunded.",
        )

    payment.status = "REFUNDED"
    payment.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(payment)

    logger.info(
        "Payment REFUNDED id=%d policy_id=%d amount=%.2f",
        payment.id, payment.policy_id, payment.amount,
    )
    return payment


@router.get("/", response_model=list[PaymentResponse])
async def list_payments(
    # Lab6: optional filters — used by API Gateway composition endpoint
    customer_id: Optional[int] = Query(default=None, description="Filter by customer ID"),
    policy_id: Optional[int] = Query(default=None, description="Filter by policy ID"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Payment).order_by(Payment.id)
    if customer_id is not None:
        stmt = stmt.where(Payment.customer_id == customer_id)
    if policy_id is not None:
        stmt = stmt.where(Payment.policy_id == policy_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: int, db: AsyncSession = Depends(get_db)):
    payment = await db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment
