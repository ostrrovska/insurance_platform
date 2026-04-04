"""
API Composition endpoints — Lab 6.

Business case: Insurance Customer Dashboard
────────────────────────────────────────────
A client app (mobile/web) needs a single API call that returns all
relevant data for a customer in one shot, instead of making 3 separate
calls and joining the data client-side.

This endpoint performs PARALLEL requests to 3 downstream services:
  1. customer_service  → customer details
  2. policy_service    → all policies for the customer
  3. payment_service   → all payments for the customer

Then it assembles a unified dashboard response with summary stats.

Resilience:
  If any upstream service is unavailable, the endpoint returns PARTIAL
  data for the services that responded, plus an "errors" section
  describing what failed. The status field is "partial" vs "complete".
  This prevents a single downstream failure from breaking the entire
  dashboard.

Endpoints:
  GET /api/v1/composition/customer/{id}/dashboard
      Full customer dashboard: profile + all policies + all payments + summary

  GET /api/v1/composition/policy/{id}/details
      Policy deep-dive: policy info + owner customer info + payment history
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.upstream_client import (
    fetch_customer,
    fetch_policies_by_customer,
    fetch_payments_by_customer,
    fetch_policy,
    fetch_payments_by_policy,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["API Composition"])


def _compute_summary(policies: list | None, payments: list | None) -> dict | None:
    """
    Compute aggregate stats from policies and payments lists.
    Returns None if both inputs are unavailable.
    """
    if policies is None and payments is None:
        return None

    summary: dict[str, Any] = {}

    if policies is not None:
        active = [p for p in policies if p.get("status") == "ACTIVE"]
        cancelled = [p for p in policies if p.get("status") == "CANCELLED"]
        pending = [p for p in policies if p.get("status") == "PENDING"]
        total_coverage = sum(p.get("coverage_amount", 0) for p in active)
        summary.update({
            "total_policies": len(policies),
            "active_policies": len(active),
            "pending_policies": len(pending),
            "cancelled_policies": len(cancelled),
            "total_active_coverage": total_coverage,
        })
    else:
        summary["policies"] = "unavailable"

    if payments is not None:
        completed = [p for p in payments if p.get("status") == "COMPLETED"]
        refunded = [p for p in payments if p.get("status") == "REFUNDED"]
        total_paid = sum(p.get("amount", 0) for p in completed)
        total_refunded = sum(p.get("amount", 0) for p in refunded)
        summary.update({
            "total_payments": len(payments),
            "completed_payments": len(completed),
            "refunded_payments": len(refunded),
            "total_paid": round(total_paid, 2),
            "total_refunded": round(total_refunded, 2),
        })
    else:
        summary["payments"] = "unavailable"

    return summary


@router.get("/customer/{customer_id}/dashboard")
async def customer_dashboard(customer_id: int):
    """
    Aggregate dashboard for a customer.

    Performs 3 PARALLEL HTTP calls to downstream services and merges
    the results. Returns partial data with errors map if any service fails.

    Response shape:
      {
        "status": "complete" | "partial",
        "customer": {...} | null,
        "policies": [...] | null,
        "payments": [...] | null,
        "summary": {...} | null,
        "errors": {"service_name": "error message", ...}
      }
    """
    logger.info("Composing dashboard for customer_id=%d", customer_id)

    # ── Fire all 3 requests in PARALLEL ───────────────────────────────────
    # asyncio.gather runs coroutines concurrently — total latency ≈ max(t1, t2, t3)
    # instead of t1 + t2 + t3 (sequential).
    (customer, customer_err), (policies, policies_err), (payments, payments_err) = (
        await asyncio.gather(
            fetch_customer(customer_id),
            fetch_policies_by_customer(customer_id),
            fetch_payments_by_customer(customer_id),
        )
    )

    # Collect errors from any failed calls
    errors: dict[str, str] = {}
    if customer_err:
        errors["customer_service"] = customer_err
    if policies_err:
        errors["policy_service"] = policies_err
    if payments_err:
        errors["payment_service"] = payments_err

    # If the customer itself is not found (404), return 404 immediately
    if customer is None and "not found" in (customer_err or ""):
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    overall_status = "partial" if errors else "complete"

    logger.info(
        "Dashboard for customer_id=%d assembled (status=%s, errors=%s)",
        customer_id, overall_status, list(errors.keys()),
    )

    return {
        "status": overall_status,
        "customer": customer,
        "policies": policies,
        "payments": payments,
        "summary": _compute_summary(policies, payments),
        "errors": errors,
    }


@router.get("/policy/{policy_id}/details")
async def policy_details(policy_id: int):
    """
    Deep-dive view for a single policy.

    Performs 2 PARALLEL HTTP calls:
      1. policy_service  → policy record
      2. payment_service → all payments for this policy

    Then fetches customer info based on the policy's customer_id.

    Response shape:
      {
        "status": "complete" | "partial",
        "policy": {...} | null,
        "customer": {...} | null,
        "payments": [...] | null,
        "payment_summary": { "total_paid": ..., "payment_count": ... } | null,
        "errors": {...}
      }
    """
    logger.info("Composing details for policy_id=%d", policy_id)

    # ── Step 1: Fetch policy and its payments in PARALLEL ─────────────────
    (policy, policy_err), (payments, payments_err) = await asyncio.gather(
        fetch_policy(policy_id),
        fetch_payments_by_policy(policy_id),
    )

    errors: dict[str, str] = {}
    if policy_err:
        errors["policy_service"] = policy_err
    if payments_err:
        errors["payment_service"] = payments_err

    if policy is None and "not found" in (policy_err or ""):
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    # ── Step 2: Fetch the policy owner's details ───────────────────────────
    customer = None
    customer_err = None
    if policy is not None:
        customer, customer_err = await fetch_customer(policy["customer_id"])
        if customer_err:
            errors["customer_service"] = customer_err

    # Build payment summary
    payment_summary = None
    if payments is not None:
        completed = [p for p in payments if p.get("status") == "COMPLETED"]
        refunded = [p for p in payments if p.get("status") == "REFUNDED"]
        payment_summary = {
            "payment_count": len(payments),
            "completed_count": len(completed),
            "total_paid": round(sum(p.get("amount", 0) for p in completed), 2),
            "total_refunded": round(sum(p.get("amount", 0) for p in refunded), 2),
        }

    overall_status = "partial" if errors else "complete"

    logger.info(
        "Policy details for policy_id=%d assembled (status=%s, errors=%s)",
        policy_id, overall_status, list(errors.keys()),
    )

    return {
        "status": overall_status,
        "policy": policy,
        "customer": customer,
        "payments": payments,
        "payment_summary": payment_summary,
        "errors": errors,
    }
