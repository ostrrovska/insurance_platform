from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@localhost:5439/policy_db"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    CUSTOMER_SERVICE_URL: str = "http://localhost:8001"
    SERVICE_PORT: int = 8002
    OUTBOX_POLL_INTERVAL: float = 2.0
    OUTBOX_BATCH_SIZE: int = 10

    class Config:
        env_file = ".env"


settings = Settings()
