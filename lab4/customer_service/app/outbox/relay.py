"""
Outbox Relay — polls the outbox table and publishes pending events.

This is the "relay" (or forwarding agent) component of the
Transactional Outbox pattern. It runs as a background asyncio task.

Guarantees:
  • At-least-once delivery (an event may be re-sent if the relay
    crashes after publishing but before marking SENT).
  • Events are published in order per aggregate (by id ASC).
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

import aio_pika
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.outbox import OutboxMessage, OutboxStatus

logger = logging.getLogger(__name__)


class OutboxRelay:
    def __init__(self):
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None

    async def _get_channel(self) -> aio_pika.abc.AbstractChannel:
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        return await self._connection.channel()

    async def _publish(self, msg: OutboxMessage) -> None:
        channel = await self._get_channel()
        # Declare exchange as durable so it survives broker restarts
        exchange = await channel.declare_exchange(
            msg.exchange, aio_pika.ExchangeType.TOPIC, durable=True
        )
        await exchange.publish(
            aio_pika.Message(
                body=msg.payload.encode(),
                content_type="application/json",
                headers={"event_type": msg.event_type},
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=msg.routing_key,
        )
        await channel.close()

    async def _process_batch(self) -> int:
        """Returns number of messages processed."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(OutboxMessage)
                .where(OutboxMessage.status.in_([OutboxStatus.PENDING, OutboxStatus.FAILED]))
                .order_by(OutboxMessage.id)
                .limit(settings.OUTBOX_BATCH_SIZE)
                .with_for_update(skip_locked=True)   # safe for concurrent relays
            )
            messages = result.scalars().all()

            for msg in messages:
                try:
                    await self._publish(msg)
                    msg.status = OutboxStatus.SENT
                    msg.sent_at = datetime.now(timezone.utc)
                    logger.info(
                        "Published event '%s' (id=%d) → exchange='%s' key='%s'",
                        msg.event_type, msg.id, msg.exchange, msg.routing_key,
                    )
                except Exception as exc:
                    msg.error = str(exc)
                    logger.error("Failed to publish outbox message id=%d: %s", msg.id, exc)

            await session.commit()
            return len(messages)

    async def run(self) -> None:
        logger.info("Outbox Relay running (poll interval=%.1fs)", settings.OUTBOX_POLL_INTERVAL)
        while True:
            try:
                count = await self._process_batch()
                if count:
                    logger.debug("Relay processed %d message(s).", count)
            except Exception as exc:
                logger.warning("Relay sweep error: %s", exc)
            await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL)
