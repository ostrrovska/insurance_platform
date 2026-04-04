"""Calls Customer Service to verify a customer exists."""

import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)


class CustomerServiceClient:
    def __init__(self):
        self.base_url = settings.CUSTOMER_SERVICE_URL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )
    async def get_customer(self, customer_id: int) -> dict | None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                r = await client.get(f"{self.base_url}/api/v1/customers/{customer_id}")
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                return r.json()
            except httpx.HTTPStatusError as exc:
                logger.error("Customer service HTTP error: %s", exc)
                raise


customer_client = CustomerServiceClient()
