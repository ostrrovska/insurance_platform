"""
Event handlers — one function per event_type.

Lab5 adds handlers for PolicyActivated and PolicyCancelled so we can
observe the saga outcome in the notification log.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def handle_customer_created(data: dict, session: AsyncSession) -> None:
    logger.info(
        "[CustomerCreated] Welcome email → customer_id=%s name='%s' email='%s'",
        data.get("customer_id"),
        data.get("name"),
        data.get("email"),
    )


async def handle_policy_created(data: dict, session: AsyncSession) -> None:
    logger.info(
        "[PolicyCreated] Policy created (status=%s) → policy_id=%s customer_id=%s type='%s'",
        data.get("status"),
        data.get("policy_id"),
        data.get("customer_id"),
        data.get("policy_type"),
    )


async def handle_policy_activated(data: dict, session: AsyncSession) -> None:
    """Saga completed successfully — policy is now active."""
    logger.info(
        "[PolicyActivated] SAGA SUCCESS — policy_id=%s customer_id=%s is now ACTIVE",
        data.get("policy_id"),
        data.get("customer_id"),
    )
    # In production: send policy confirmation email, generate PDF certificate, etc.


async def handle_policy_cancelled(data: dict, session: AsyncSession) -> None:
    """Saga compensation executed — policy was rolled back."""
    logger.info(
        "[PolicyCancelled] SAGA COMPENSATED — policy_id=%s customer_id=%s was CANCELLED (reason: payment failed)",
        data.get("policy_id"),
        data.get("customer_id"),
    )
    # In production: send apology email, notify underwriting team, etc.


# Registry maps event_type → handler function
EVENT_HANDLERS = {
    "CustomerCreated": handle_customer_created,
    "PolicyCreated": handle_policy_created,
    "PolicyActivated": handle_policy_activated,
    "PolicyCancelled": handle_policy_cancelled,
}
