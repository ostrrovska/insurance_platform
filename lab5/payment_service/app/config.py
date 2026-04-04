from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@localhost:5440/payment_db"
    SERVICE_PORT: int = 8003

    class Config:
        env_file = ".env"


settings = Settings()
