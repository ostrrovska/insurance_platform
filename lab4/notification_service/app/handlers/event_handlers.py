"""
Event handlers — one function per event_type.
Each handler receives the parsed envelope dict and a DB session.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def handle_customer_created(data: dict, session: AsyncSession) -> None:
    logger.info(
        "📧 [CustomerCreated] Welcome email → customer_id=%s name='%s' email='%s'",
        data.get("customer_id"),
        data.get("name"),
        data.get("email"),
    )
    # In production: send welcome email, create CRM record, etc.


async def handle_policy_created(data: dict, session: AsyncSession) -> None:
    logger.info(
        "📋 [PolicyCreated] Policy confirmation → policy_id=%s customer_id=%s type='%s'",
        data.get("policy_id"),
        data.get("customer_id"),
        data.get("policy_type"),
    )
    # In production: send policy PDF, trigger underwriting workflow, etc.


# Registry maps event_type → handler function
EVENT_HANDLERS = {
    "CustomerCreated": handle_customer_created,
    "PolicyCreated": handle_policy_created,
}
