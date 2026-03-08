import uuid
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict # Added SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Customer Service API"
    app_version: str = "1.0.0"
    host: str = "127.0.0.1"
    port: int = 8001
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
app = FastAPI(title=settings.app_name)

CUSTOMERS_DB = {
    1: {"id": 1, "name": "John Doe", "email": "john@example.com", "risk_score": 15}
}


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str
    risk_score: int


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.get("/api/v1/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: int, request: Request):
    # Log the request with Correlation ID for tracing
    print(f"[Trace: {request.state.correlation_id}] Fetching customer {customer_id}")

    customer = CUSTOMERS_DB.get(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=settings.port, reload=True)