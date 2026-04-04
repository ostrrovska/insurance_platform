"""
API Gateway — path-based proxy routing.

Maps the first URL segment after /api/v1/ to an upstream service and
forwards the full request (method, headers, body, query params).

Routing table (defined in config.py):
  /api/v1/customers/...     → customer_service:8001
  /api/v1/policies/...      → policy_service:8002
  /api/v1/payments/...      → payment_service:8003
  /api/v1/notifications/... → notification_service:8004
  /api/v1/sagas/...         → saga_orchestrator:8005

The /api/v1/composition/... prefix is handled by composition.py and is
registered BEFORE this catch-all, so it takes precedence.
"""

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.config import SERVICE_ROUTES

logger = logging.getLogger(__name__)

router = APIRouter()

# Headers that should NOT be forwarded to the upstream service
_HOP_BY_HOP = frozenset({
    "host", "content-length", "transfer-encoding",
    "connection", "keep-alive", "te", "trailers", "upgrade",
})


@router.api_route(
    "/api/v1/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=True,
    name="proxy",
    summary="Proxy to internal microservice",
    description=(
        "Forwards the request to the appropriate internal service based on "
        "the first path segment. E.g. /api/v1/customers/1 → customer_service."
    ),
)
async def proxy_request(path: str, request: Request) -> Response:
    """
    Path-based reverse proxy.

    Strips /api/v1/ prefix, reads the first segment (resource name),
    looks up the upstream URL, and forwards the full request.
    """
    # Extract the resource name from the first path segment
    # e.g. path="customers/1" → resource="customers"
    resource = path.split("/")[0]

    upstream_base = SERVICE_ROUTES.get(resource)
    if not upstream_base:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No upstream service mapped for resource '{resource}'. "
                f"Known resources: {list(SERVICE_ROUTES.keys())}"
            ),
        )

    # Build the full upstream URL, preserving query string
    upstream_url = f"{upstream_base}/api/v1/{path}"
    if request.query_params:
        upstream_url += "?" + str(request.query_params)

    # Filter headers — strip hop-by-hop headers but keep everything else
    forwarded_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }
    # Add X-Forwarded-For to indicate request came through the gateway
    forwarded_headers["X-Forwarded-For"] = request.client.host if request.client else "unknown"
    forwarded_headers["X-Gateway"] = "api-gateway"

    # Read request body (for POST/PUT/PATCH)
    body = await request.body()

    logger.info(
        "PROXY %s %s → %s",
        request.method, request.url.path, upstream_url,
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            upstream_response = await client.request(
                method=request.method,
                url=upstream_url,
                headers=forwarded_headers,
                content=body,
            )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Upstream service '{resource}' is unavailable (connection refused).",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Upstream service '{resource}' timed out.",
        )
    except httpx.HTTPError as exc:
        logger.error("Proxy error forwarding to %s: %s", upstream_url, exc)
        raise HTTPException(status_code=502, detail=f"Bad gateway: {exc}")

    # Forward the upstream response back to the client
    # Strip hop-by-hop response headers too
    response_headers = {
        k: v for k, v in upstream_response.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )
