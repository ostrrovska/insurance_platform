import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.api.payments import router as payments_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Payment Service...")
    await init_db()
    yield
    logger.info("Payment Service stopped.")


app = FastAPI(
    title="Payment Service",
    description=(
        "Handles premium payments for insurance policies. "
        "Participates in the Policy Purchase Saga as Step 3. "
        "Supports compensation via the /refund endpoint."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(payments_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "payment_service"}
