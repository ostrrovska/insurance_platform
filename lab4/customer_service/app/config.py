from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@localhost:5433/customer_db"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    SERVICE_PORT: int = 8001
    OUTBOX_POLL_INTERVAL: float = 2.0   # seconds between relay sweeps
    OUTBOX_BATCH_SIZE: int = 10

    class Config:
        env_file = ".env"


settings = Settings()
