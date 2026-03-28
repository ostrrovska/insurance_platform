"""
Outbox Relay for Policy Service.
Polls the outbox table and publishes pending events to RabbitMQ.
"""

import asyncio
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
        self._connection = None

    async def _drop_connection(self) -> None:
        """After broker failures, robust client may stay half-open; force a new TCP session."""
        conn = self._connection
        self._connection = None
        if conn is not None and not conn.is_closed:
            try:
                await conn.close()
            except Exception:
                pass

    async def _get_channel(self):
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        return await self._connection.channel()

    async def _publish(self, msg: OutboxMessage) -> None:
        channel = await self._get_channel()
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
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(OutboxMessage)
                .where(
                    OutboxMessage.status.in_(
                        [OutboxStatus.PENDING, OutboxStatus.FAILED]
                    )
                )
                .order_by(OutboxMessage.id)
                .limit(settings.OUTBOX_BATCH_SIZE)
                .with_for_update(skip_locked=True)
            )
            messages = result.scalars().all()

            for msg in messages:
                try:
                    await self._publish(msg)
                    msg.status = OutboxStatus.SENT
                    msg.error = None
                    msg.sent_at = datetime.now(timezone.utc)
                    logger.info(
                        "Published '%s' (id=%d) → exchange='%s' key='%s'",
                        msg.event_type, msg.id, msg.exchange, msg.routing_key,
                    )
                except Exception as exc:
                    msg.status = OutboxStatus.FAILED
                    msg.error = str(exc)
                    logger.error("Failed to publish outbox id=%d: %s", msg.id, exc)
                    await self._drop_connection()

            await session.commit()
            return len(messages)

    async def run(self) -> None:
        logger.info("Outbox Relay running (interval=%.1fs)", settings.OUTBOX_POLL_INTERVAL)
        while True:
            try:
                await self._process_batch()
            except Exception as exc:
                logger.warning("Relay sweep error: %s", exc)
            await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL)
