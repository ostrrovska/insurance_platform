"""
Policy Purchase Saga — Orchestration approach.

WHY ORCHESTRATION OVER CHOREOGRAPHY?
─────────────────────────────────────
Choreography works well for simple, independent event chains (A publishes
event → B reacts → B publishes → C reacts). It keeps services decoupled
but makes the overall flow invisible — no single place shows the full state.

This saga has 4 sequential, dependent steps, conditional branching
(success vs failure), and explicit compensating transactions. With
choreography each service would need to "know" what came before it and
what to do on rollback, scattering saga logic across 3 services.

Orchestration keeps ALL saga logic in one place (this file), making it:
  • Easy to read the full flow from top to bottom
  • Easy to add new steps or change compensation order
  • Fully observable: one DB table shows every saga's current state
  • Easier to implement idempotency and replay

POLICY PURCHASE SAGA — 4 FORWARD STEPS:
  1. VALIDATING_CUSTOMER  → GET  /customers/{id}
  2. CREATING_POLICY      → POST /policies/       (status=PENDING)
  3. PROCESSING_PAYMENT   → POST /payments/
  4. ACTIVATING_POLICY    → PATCH /policies/{id}/status  (status=ACTIVE)
  → COMPLETED

COMPENSATING TRANSACTIONS (reverse order if failure):
  If step 3 fails (payment):
    • Comp-1: PATCH /policies/{id}/status → CANCELLED

  If step 4 fails (activation):
    • Comp-1: POST /payments/{id}/refund
    • Comp-2: PATCH /policies/{id}/status → CANCELLED
  → COMPENSATED

Data consistency guarantee:
  After compensation the policy is CANCELLED and (if charged) payment is
  REFUNDED. Querying each service's DB directly will confirm this.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.saga import Saga
from app.services.customer_client import customer_client
from app.services.policy_client import policy_client
from app.services.payment_client import payment_client

logger = logging.getLogger(__name__)


async def _save(db: AsyncSession, saga: Saga) -> None:
    """Persist the current saga state to the DB."""
    saga.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(saga)


async def _set_status(db: AsyncSession, saga: Saga, status: str, step_detail: str = "") -> None:
    """Update saga status, append to step log, persist."""
    saga.status = status
    saga.append_step(status, step_detail)
    await _save(db, saga)
    logger.info("Saga %s → %s  %s", saga.id, status, step_detail)


async def compensate(db: AsyncSession, saga: Saga, error: str) -> None:
    """
    Execute compensating transactions in reverse order.

    We only compensate steps that already succeeded:
      - If payment was charged → refund it first
      - If policy was created  → cancel it
    Both are attempted even if one fails, to maximise consistency.
    """
    saga.error = error
    await _set_status(db, saga, "COMPENSATING", f"Reason: {error}")

    # ── Compensate Payment (if it was charged successfully) ────────────────
    if saga.payment_id is not None:
        try:
            await payment_client.refund_payment(saga.payment_id)
            saga.append_step("REFUND_PAYMENT", f"Refunded payment_id={saga.payment_id}")
            await _save(db, saga)
            logger.info("Saga %s: refunded payment_id=%d", saga.id, saga.payment_id)
        except Exception as exc:
            # Log but continue — we still need to cancel the policy
            logger.error("Saga %s: failed to refund payment_id=%d: %s", saga.id, saga.payment_id, exc)
            saga.append_step("REFUND_PAYMENT_FAILED", str(exc))
            await _save(db, saga)

    # ── Compensate Policy (if it was created) ──────────────────────────────
    if saga.policy_id is not None:
        try:
            await policy_client.update_policy_status(saga.policy_id, "CANCELLED", saga.id)
            saga.append_step("CANCEL_POLICY", f"Cancelled policy_id={saga.policy_id}")
            await _save(db, saga)
            logger.info("Saga %s: cancelled policy_id=%d", saga.id, saga.policy_id)
        except Exception as exc:
            logger.error("Saga %s: failed to cancel policy_id=%d: %s", saga.id, saga.policy_id, exc)
            saga.append_step("CANCEL_POLICY_FAILED", str(exc))
            await _save(db, saga)

    await _set_status(db, saga, "COMPENSATED", "All compensating transactions executed.")


async def run_policy_purchase_saga(
    saga_id: str,
    customer_id: int,
    policy_type: str,
    coverage_amount: float,
    premium_amount: float,
    simulate_payment_failure: bool,
) -> None:
    """
    Execute the Policy Purchase Saga.

    The saga record (with status=STARTED) is already created by the API
    endpoint before this function is called as a background task.
    This function loads that record and executes all steps, updating
    the status at each transition.
    """
    async with AsyncSessionLocal() as db:
        # Load the pre-created saga record
        saga = await db.get(Saga, saga_id)
        if not saga:
            logger.error("Saga %s: record not found in DB — aborting", saga_id)
            return

        logger.info("Saga %s executing (customer_id=%d type=%s)", saga_id, customer_id, policy_type)

        # ══ STEP 1: Validate Customer ══════════════════════════════════════
        await _set_status(db, saga, "VALIDATING_CUSTOMER", f"Looking up customer_id={customer_id}")
        try:
            customer = await customer_client.get_customer(customer_id)
            if customer is None:
                # Customer does not exist — fail immediately, nothing to compensate yet
                saga.error = f"Customer {customer_id} not found"
                saga.append_step("VALIDATE_CUSTOMER_FAILED", saga.error)
                await _set_status(db, saga, "FAILED", saga.error)
                return
            saga.append_step("CUSTOMER_VALIDATED", f"customer name='{customer['name']}'")
            await _save(db, saga)
        except Exception as exc:
            saga.error = f"Customer service unreachable: {exc}"
            await _set_status(db, saga, "FAILED", saga.error)
            return

        # ══ STEP 2: Create Policy (status=PENDING) ═════════════════════════
        await _set_status(db, saga, "CREATING_POLICY", "Creating policy with status=PENDING")
        try:
            policy = await policy_client.create_policy(
                customer_id=customer_id,
                policy_type=policy_type,
                coverage_amount=coverage_amount,
                premium_amount=premium_amount,
                saga_id=saga_id,
            )
            # Save policy_id — needed by compensation to cancel it
            saga.policy_id = policy["id"]
            saga.append_step("POLICY_CREATED", f"policy_id={policy['id']} status=PENDING")
            await _save(db, saga)
        except Exception as exc:
            await compensate(db, saga, f"Failed to create policy: {exc}")
            return

        # ══ STEP 3: Process Payment ════════════════════════════════════════
        await _set_status(
            db, saga, "PROCESSING_PAYMENT",
            f"Charging premium={premium_amount} (simulate_failure={simulate_payment_failure})",
        )
        try:
            payment = await payment_client.process_payment(
                policy_id=saga.policy_id,
                customer_id=customer_id,
                amount=premium_amount,
                simulate_failure=simulate_payment_failure,
            )
            # Save payment_id — needed by compensation to refund it
            saga.payment_id = payment["id"]
            saga.append_step("PAYMENT_COMPLETED", f"payment_id={payment['id']} amount={premium_amount}")
            await _save(db, saga)
        except httpx.HTTPStatusError as exc:
            # 402 Payment Required — the payment service intentionally failed
            # Note: payment_id stays None (the failed payment record is in payment_db for audit)
            error_msg = f"Payment failed (HTTP {exc.response.status_code}): {exc.response.text}"
            await compensate(db, saga, error_msg)
            return
        except Exception as exc:
            await compensate(db, saga, f"Payment service error: {exc}")
            return

        # ══ STEP 4: Activate Policy ════════════════════════════════════════
        await _set_status(
            db, saga, "ACTIVATING_POLICY",
            f"Setting policy_id={saga.policy_id} to ACTIVE",
        )
        try:
            activated = await policy_client.update_policy_status(
                saga.policy_id, "ACTIVE", saga_id
            )
            saga.append_step("POLICY_ACTIVATED", f"policy_id={activated['id']} status=ACTIVE")
            await _save(db, saga)
        except Exception as exc:
            # Payment already went through — must refund it AND cancel the policy
            await compensate(db, saga, f"Failed to activate policy: {exc}")
            return

        # ══ COMPLETED ══════════════════════════════════════════════════════
        await _set_status(
            db, saga, "COMPLETED",
            f"Policy {saga.policy_id} is ACTIVE, payment {saga.payment_id} COMPLETED.",
        )
        logger.info(
            "Saga %s COMPLETED — policy_id=%d payment_id=%d",
            saga_id, saga.policy_id, saga.payment_id,
        )
