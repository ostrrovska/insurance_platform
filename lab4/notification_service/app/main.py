import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import init_db, get_db
from app.consumers.rabbit_consumer import RabbitMQConsumer
from app.models.notification import Notification

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Notification Service...")
    await init_db()

    consumer = RabbitMQConsumer()
    consumer_task = asyncio.create_task(consumer.run())
    logger.info("RabbitMQ Consumer started.")

    yield

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    logger.info("Notification Service stopped.")


app = FastAPI(
    title="Notification Service",
    description="Async consumer — subscribes to domain events and processes notifications.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "notification_service"}


@app.get("/api/v1/notifications")
async def list_notifications(db: AsyncSession = Depends(get_db)):
    """Returns all processed events — useful for verifying delivery."""
    result = await db.execute(
        select(Notification).order_by(Notification.processed_at.desc()).limit(50)
    )
    notifications = result.scalars().all()
    return [
        {
            "id": n.id,
            "event_id": n.event_id,
            "event_type": n.event_type,
            "routing_key": n.routing_key,
            "processed_at": n.processed_at.isoformat(),
        }
        for n in notifications
    ]
