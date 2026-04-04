"""
API Gateway Service — Lab 6

Implements two Lab 6 requirements in a single FastAPI service:

1. API GATEWAY (Routing)
   ─────────────────────
   All external traffic enters through port 8000. The gateway proxies
   each request to the correct internal service based on the URL path:

     /api/v1/customers/...     → customer_service:8001
     /api/v1/policies/...      → policy_service:8002
     /api/v1/payments/...      → payment_service:8003
     /api/v1/notifications/... → notification_service:8004
     /api/v1/sagas/...         → saga_orchestrator:8005

   Internal services are NOT exposed to clients — only the gateway is.
   (In production you would restrict internal ports at the network level.)

2. API COMPOSITION (BFF pattern)
   ──────────────────────────────
   The gateway exposes two composition endpoints that aggregate data from
   multiple services in PARALLEL using asyncio.gather:

     GET /api/v1/composition/customer/{id}/dashboard
       Parallel calls to: customer_service + policy_service + payment_service
       Returns: unified customer dashboard with summary stats

     GET /api/v1/composition/policy/{id}/details
       Parallel calls to: policy_service + payment_service, then customer_service
       Returns: policy + payment history + owner details

   RESILIENCE: if any upstream service is unavailable, the endpoint returns
   partial data (services that responded) + an "errors" section explaining
   what failed. The overall "status" field is "partial" instead of "complete".
   This prevents a single downstream outage from breaking the entire dashboard.

Router registration order matters:
  1. composition_router  — specific prefix /api/v1/composition/, matched first
  2. proxy_router        — catch-all /api/v1/{path:path}, matched last
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.composition import router as composition_router
from app.api.proxy import router as proxy_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API Gateway starting on port 8000...")
    yield
    logger.info("API Gateway stopped.")


app = FastAPI(
    title="API Gateway",
    description=(
        "Single entry point for the Insurance Platform. "
        "Provides path-based routing to internal microservices "
        "and API Composition endpoints that aggregate data in parallel."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── Register composition routes FIRST (specific prefix takes precedence) ──
# These handle /api/v1/composition/... and must be registered before the
# catch-all proxy route, otherwise the proxy would intercept them.
app.include_router(composition_router, prefix="/api/v1/composition")

# ── Register proxy catch-all LAST ─────────────────────────────────────────
# This route handles /api/v1/{anything} and forwards to the correct service.
app.include_router(proxy_router)


@app.get("/health", tags=["Gateway"])
async def health():
    return {"status": "ok", "service": "api_gateway"}


@app.get("/", tags=["Gateway"])
async def root():
    """Lists available routes for discoverability."""
    return {
        "service": "API Gateway",
        "description": "Single entry point for the Insurance Platform",
        "routing": {
            "/api/v1/customers/*":     "→ customer_service:8001",
            "/api/v1/policies/*":      "→ policy_service:8002",
            "/api/v1/payments/*":      "→ payment_service:8003",
            "/api/v1/notifications/*": "→ notification_service:8004",
            "/api/v1/sagas/*":         "→ saga_orchestrator:8005",
        },
        "composition": {
            "/api/v1/composition/customer/{id}/dashboard": "Aggregated customer view (parallel)",
            "/api/v1/composition/policy/{id}/details":     "Policy deep-dive (parallel)",
        },
        "docs": "/docs",
    }
