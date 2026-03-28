"""Helpers for writing events into the outbox table."""

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxMessage


async def publish_event(
    session: AsyncSession,
    *,
    event_type: str,
    exchange: str,
    routing_key: str,
    payload: dict,
) -> OutboxMessage:
    """
    Write an event to the outbox table inside the CURRENT session/transaction.
    The relay will pick it up and forward it to RabbitMQ.
    """
    envelope = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }
    msg = OutboxMessage(
        event_type=event_type,
        exchange=exchange,
        routing_key=routing_key,
        payload=json.dumps(envelope),
    )
    session.add(msg)
    return msg
