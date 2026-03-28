import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.outbox.relay import OutboxRelay
from app.api.policies import router as policies_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Policy Service...")
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
    logger.info("Policy Service stopped.")


app = FastAPI(
    title="Policy Service",
    description="Manages insurance policies. Publishes events via Transactional Outbox.",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(policies_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "policy_service"}
