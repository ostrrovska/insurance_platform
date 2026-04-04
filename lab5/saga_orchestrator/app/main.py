"""
Saga Orchestrator Service — Lab 5

Implements the ORCHESTRATION variant of the Saga pattern for the
Policy Purchase distributed business transaction.

Architecture choice: Orchestration vs Choreography
────────────────────────────────────────────────────
We chose ORCHESTRATION because:

1. The saga has 4 sequential, dependent steps — each step needs the
   result of the previous one (e.g. policy_id from step 2 is needed
   in step 3 and 4). Choreography would require passing this context
   through events, making each service tightly coupled to the event schema.

2. The compensation logic must run in a specific order (reverse of forward
   steps). With choreography, each service would need to know "what to undo"
   in response to failure events, scattering rollback logic everywhere.

3. Observability: with a central orchestrator we have ONE place (the sagas
   table) that shows the complete saga state at any moment. With choreography
   you'd need to correlate events across multiple services' logs/queues.

4. This platform already uses the Outbox + RabbitMQ pattern (from lab4) for
   loose coupling between services. The orchestrator sits on top of HTTP APIs
   and doesn't replace the async event bus — it complements it.

Saga Steps:
  1. Validate Customer  (GET  customer_service:8001/api/v1/customers/{id})
  2. Create Policy      (POST policy_service:8002/api/v1/policies/)
  3. Process Payment    (POST payment_service:8003/api/v1/payments/)
  4. Activate Policy    (PATCH policy_service:8002/api/v1/policies/{id}/status)

Compensating Transactions (run in reverse if any step fails):
  • If payment fails    → PATCH policy → CANCELLED
  • If activation fails → POST payment/refund + PATCH policy → CANCELLED
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.api.sagas import router as sagas_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Saga Orchestrator Service...")
    await init_db()
    yield
    logger.info("Saga Orchestrator Service stopped.")


app = FastAPI(
    title="Saga Orchestrator",
    description=(
        "Central coordinator for the Policy Purchase Saga. "
        "Implements the ORCHESTRATION pattern: all saga logic lives here, "
        "services are called via HTTP, and compensating transactions are "
        "executed automatically on failure."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(sagas_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "saga_orchestrator"}
