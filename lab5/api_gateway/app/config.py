from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Upstream service URLs (internal Docker network names)
    CUSTOMER_SERVICE_URL: str = "http://localhost:8001"
    POLICY_SERVICE_URL: str = "http://localhost:8002"
    PAYMENT_SERVICE_URL: str = "http://localhost:8003"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8004"
    SAGA_ORCHESTRATOR_URL: str = "http://localhost:8005"

    SERVICE_PORT: int = 8000

    # Timeout for upstream HTTP calls (seconds).
    # Composition endpoints use this for each parallel call.
    UPSTREAM_TIMEOUT: float = 5.0

    class Config:
        env_file = ".env"


settings = Settings()

# Routing table: first URL segment after /api/v1/ → upstream base URL.
# Used by the proxy layer to forward requests.
SERVICE_ROUTES: dict[str, str] = {
    "customers":     settings.CUSTOMER_SERVICE_URL,
    "policies":      settings.POLICY_SERVICE_URL,
    "payments":      settings.PAYMENT_SERVICE_URL,
    "notifications": settings.NOTIFICATION_SERVICE_URL,
    "sagas":         settings.SAGA_ORCHESTRATOR_URL,
}
