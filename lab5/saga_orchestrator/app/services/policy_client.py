"""HTTP client for Policy Service."""

import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class PolicyClient:
    def __init__(self):
        self.base_url = settings.POLICY_SERVICE_URL

    async def create_policy(
        self,
        customer_id: int,
        policy_type: str,
        coverage_amount: float,
        premium_amount: float,
        saga_id: str,
    ) -> dict:
        """
        Create a new policy with status=PENDING.
        Raises httpx.HTTPError if the request fails.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/policies/",
                json={
                    "customer_id": customer_id,
                    "policy_type": policy_type,
                    "coverage_amount": coverage_amount,
                    "premium_amount": premium_amount,
                    "status": "PENDING",
                },
                # Pass saga_id as correlation ID for tracing
                headers={"X-Correlation-ID": saga_id},
            )
            r.raise_for_status()
            return r.json()

    async def update_policy_status(
        self, policy_id: int, new_status: str, saga_id: str
    ) -> dict:
        """
        Change a policy's status (PENDING→ACTIVE or PENDING→CANCELLED).
        Raises httpx.HTTPError if the request fails.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.patch(
                f"{self.base_url}/api/v1/policies/{policy_id}/status",
                json={"status": new_status},
                headers={"X-Correlation-ID": saga_id},
            )
            r.raise_for_status()
            return r.json()


policy_client = PolicyClient()
