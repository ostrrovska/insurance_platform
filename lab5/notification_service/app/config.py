from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@localhost:5441/notification_db"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    SERVICE_PORT: int = 8004

    # Queues & bindings
    CUSTOMERS_EXCHANGE: str = "customers"
    POLICIES_EXCHANGE: str = "policies"
    NOTIFICATION_QUEUE: str = "notification_service.events"

    class Config:
        env_file = ".env"


settings = Settings()
