"""HTTP client for Payment Service."""

import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class PaymentClient:
    def __init__(self):
        self.base_url = settings.PAYMENT_SERVICE_URL

    async def process_payment(
        self,
        policy_id: int,
        customer_id: int,
        amount: float,
        simulate_failure: bool = False,
    ) -> dict:
        """
        Process a premium payment.

        If simulate_failure=True the payment service returns 402 and this
        method raises httpx.HTTPStatusError, which the saga catches to
        trigger compensation.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/payments/",
                json={
                    "policy_id": policy_id,
                    "customer_id": customer_id,
                    "amount": amount,
                    "simulate_failure": simulate_failure,
                },
            )
            r.raise_for_status()  # raises on 4xx/5xx
            return r.json()

    async def refund_payment(self, payment_id: int) -> dict:
        """
        Refund a completed payment (compensating transaction).
        Raises httpx.HTTPError if the request fails.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{self.base_url}/api/v1/payments/{payment_id}/refund"
            )
            r.raise_for_status()
            return r.json()


payment_client = PaymentClient()
