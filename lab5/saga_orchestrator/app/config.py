from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@localhost:5442/orchestrator_db"
    CUSTOMER_SERVICE_URL: str = "http://localhost:8001"
    POLICY_SERVICE_URL: str = "http://localhost:8002"
    PAYMENT_SERVICE_URL: str = "http://localhost:8003"
    SERVICE_PORT: int = 8005

    class Config:
        env_file = ".env"


settings = Settings()
