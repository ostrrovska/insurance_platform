"""HTTP client for Customer Service."""

import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class CustomerClient:
    def __init__(self):
        self.base_url = settings.CUSTOMER_SERVICE_URL

    async def get_customer(self, customer_id: int) -> dict | None:
        """
        Fetch a customer by ID.
        Returns the customer dict or None if not found.
        Raises httpx.HTTPError on network/server errors.
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{self.base_url}/api/v1/customers/{customer_id}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()


customer_client = CustomerClient()
