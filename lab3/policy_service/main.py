import uuid
import httpx
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from resilience import CircuitBreaker

class Settings(BaseSettings):
    app_name: str = "Policy Service API"
    app_version: str = "1.0.0"
    host: str = "127.0.0.1"
    port: int = 8002
    environment: str = "development"
    customer_service_url: str = "http://127.0.0.1:8001"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
app = FastAPI(title=settings.app_name)
circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=15)

POLICIES_DB = []


class PolicyRequest(BaseModel):
    customer_id: int
    policy_type: str


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
)
async def fetch_customer_data(customer_id: int, correlation_id: str):
    print(f"[Attempting Request] Fetching customer {customer_id}")
    async with httpx.AsyncClient(timeout=2.0) as client:
        headers = {"X-Correlation-ID": correlation_id}
        url = f"{settings.customer_service_url}/api/v1/customers/{customer_id}"
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


@app.post("/api/v1/policies")
async def create_policy(policy: PolicyRequest, request: Request):
    corr_id = request.state.correlation_id

    if not circuit_breaker.can_execute():
        # Fallback response when circuit is OPEN
        return {
            "status": "failed",
            "message": "Customer service is temporarily unavailable. Cannot issue policy right now. Please try again later.",
            "fallback_triggered": True
        }

    # 2. Synchronous Call with Retries and Timeouts
    try:
        customer_data = await fetch_customer_data(policy.customer_id, corr_id)
        circuit_breaker.record_success()  # Reset on success

        # 3. Create Policy using fetched data
        new_policy = {
            "policy_id": len(POLICIES_DB) + 1,
            "customer_id": customer_data["id"],
            "type": policy.policy_type,
            "status": "ACTIVE"
        }
        POLICIES_DB.append(new_policy)
        return new_policy

    except Exception as e:
        # Record failure for Circuit Breaker
        circuit_breaker.record_failure()
        print(f"[Error] Failed to fetch customer: {str(e)}")
        raise HTTPException(status_code=503, detail="Dependent service failed after retries.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=settings.port, reload=True)