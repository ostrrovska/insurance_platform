import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.outbox.relay import OutboxRelay
from app.api.customers import router as customers_router
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Customer Service...")
    await init_db()

    relay = OutboxRelay()
    relay_task = asyncio.create_task(relay.run())
    logger.info("Outbox Relay started.")

    yield

    relay_task.cancel()
    try:
        await relay_task
    except asyncio.CancelledError:
        pass
    logger.info("Customer Service stopped.")


app = FastAPI(
    title="Customer Service",
    description="Manages customers. Publishes events via Transactional Outbox.",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(customers_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "customer_service"}
