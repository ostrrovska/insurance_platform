"""
Async RabbitMQ Consumer.

Subscribes to all events from the 'customers' and 'policies' exchanges
using a single durable queue with topic bindings.

Idempotency: Each message is stored in the notifications table keyed by
event_id. Duplicate deliveries (at-least-once) are silently dropped.
"""

import asyncio
import json
import logging

import aio_pika
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import AsyncSessionLocal
from app.handlers.event_handlers import EVENT_HANDLERS
from app.models.notification import Notification

logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    async def _setup(
        self,
    ) -> tuple[aio_pika.abc.AbstractConnection, aio_pika.abc.AbstractQueue]:
        # Plain connection + outer reconnect loop. connect_robust + asyncio.Future()
        # often leaves the process without active consumers after a broker restart.
        connection = await aio_pika.connect(settings.RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        # Declare both upstream exchanges (must match what producers declare)
        customers_exchange = await channel.declare_exchange(
            settings.CUSTOMERS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
        )
        policies_exchange = await channel.declare_exchange(
            settings.POLICIES_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
        )

        # Single durable queue — survives broker restarts
        queue = await channel.declare_queue(
            settings.NOTIFICATION_QUEUE,
            durable=True,
            arguments={"x-queue-type": "classic"},
        )

        # Bind to all routing keys from both exchanges
        await queue.bind(customers_exchange, routing_key="customers.#")
        await queue.bind(policies_exchange, routing_key="policies.#")

        logger.info(
            "Consumer ready — queue='%s' bound to exchanges [%s, %s]",
            settings.NOTIFICATION_QUEUE,
            settings.CUSTOMERS_EXCHANGE,
            settings.POLICIES_EXCHANGE,
        )
        return connection, queue

    async def _handle_message(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                envelope = json.loads(message.body.decode())
            except json.JSONDecodeError as exc:
                logger.error("Invalid JSON in message: %s", exc)
                return

            event_id = envelope.get("event_id", "unknown")
            event_type = envelope.get("event_type", "unknown")
            data = envelope.get("data", {})
            routing_key = message.routing_key or ""

            logger.info("Received event '%s' (id=%s) via '%s'", event_type, event_id, routing_key)

            async with AsyncSessionLocal() as session:
                # Idempotency check — skip if already processed
                notification = Notification(
                    event_id=event_id,
                    event_type=event_type,
                    routing_key=routing_key,
                    payload=message.body.decode(),
                )
                session.add(notification)

                try:
                    await session.flush()
                except IntegrityError:
                    await session.rollback()
                    logger.warning("Duplicate event '%s' — skipped.", event_id)
                    return

                # Dispatch to domain handler
                handler = EVENT_HANDLERS.get(event_type)
                if handler:
                    await handler(data, session)
                else:
                    logger.warning("No handler for event_type='%s'", event_type)

                await session.commit()
                logger.info("Event '%s' (id=%s) processed ✓", event_type, event_id)

    async def run(self) -> None:
        while True:
            try:
                connection, queue = await self._setup()
                await queue.consume(self._handle_message)
                logger.info("Consumer listening for messages...")
                close_event = asyncio.Event()
                connection.close_callbacks.add(lambda *_: close_event.set())
                await close_event.wait()
                logger.warning("RabbitMQ connection closed — reconnecting…")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Consumer error: %s — reconnecting in 5s", exc)
                await asyncio.sleep(5)
