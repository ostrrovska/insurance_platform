"""
Upstream HTTP client helpers used by the composition layer.

Each helper calls one downstream service and returns either the parsed
JSON or a structured error dict — it never raises. This allows the
composition endpoint to return PARTIAL data when one service is down.
"""

import asyncio
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def _safe_get(client: httpx.AsyncClient, url: str, label: str) -> tuple[Any, str | None]:
    """
    Perform a GET request and return (data, error_message).

    On success  → (json_data, None)
    On failure  → (None, error_string)
    """
    try:
        r = await client.get(url)
        if r.status_code == 404:
            return None, f"{label}: not found (404)"
        r.raise_for_status()
        return r.json(), None
    except httpx.TimeoutException:
        logger.warning("Timeout calling %s (%s)", label, url)
        return None, f"{label}: request timed out"
    except httpx.ConnectError:
        logger.warning("Connection refused calling %s (%s)", label, url)
        return None, f"{label}: service unavailable (connection refused)"
    except httpx.HTTPStatusError as exc:
        logger.warning("HTTP error from %s: %s", label, exc)
        return None, f"{label}: HTTP {exc.response.status_code}"
    except Exception as exc:
        logger.error("Unexpected error calling %s: %s", label, exc)
        return None, f"{label}: unexpected error — {exc}"


async def fetch_customer(customer_id: int) -> tuple[dict | None, str | None]:
    """Fetch a single customer from customer_service."""
    async with httpx.AsyncClient(timeout=settings.UPSTREAM_TIMEOUT) as client:
        return await _safe_get(
            client,
            f"{settings.CUSTOMER_SERVICE_URL}/api/v1/customers/{customer_id}",
            "customer_service",
        )


async def fetch_policies_by_customer(customer_id: int) -> tuple[list | None, str | None]:
    """Fetch all policies for a customer from policy_service."""
    async with httpx.AsyncClient(timeout=settings.UPSTREAM_TIMEOUT) as client:
        return await _safe_get(
            client,
            f"{settings.POLICY_SERVICE_URL}/api/v1/policies/?customer_id={customer_id}",
            "policy_service",
        )


async def fetch_payments_by_customer(customer_id: int) -> tuple[list | None, str | None]:
    """Fetch all payments for a customer from payment_service."""
    async with httpx.AsyncClient(timeout=settings.UPSTREAM_TIMEOUT) as client:
        return await _safe_get(
            client,
            f"{settings.PAYMENT_SERVICE_URL}/api/v1/payments/?customer_id={customer_id}",
            "payment_service",
        )


async def fetch_policy(policy_id: int) -> tuple[dict | None, str | None]:
    """Fetch a single policy from policy_service."""
    async with httpx.AsyncClient(timeout=settings.UPSTREAM_TIMEOUT) as client:
        return await _safe_get(
            client,
            f"{settings.POLICY_SERVICE_URL}/api/v1/policies/{policy_id}",
            "policy_service",
        )


async def fetch_payments_by_policy(policy_id: int) -> tuple[list | None, str | None]:
    """Fetch all payments for a specific policy from payment_service."""
    async with httpx.AsyncClient(timeout=settings.UPSTREAM_TIMEOUT) as client:
        return await _safe_get(
            client,
            f"{settings.PAYMENT_SERVICE_URL}/api/v1/payments/?policy_id={policy_id}",
            "payment_service",
        )
