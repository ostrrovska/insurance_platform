from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.config import settings
from customer_management.api import router as customer_router
from policy_management.api import router as policy_router
from claims_management.api import router as claims_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Modular monolith with validation, error handling, and health checks."
)

def create_error_response(status_code: int, description: str, details: any = None):
    content = {
        "error_code": status_code,
        "description": description,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if details:
        content["details"] = details
    return JSONResponse(status_code=status_code, content=content)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return create_error_response(exc.status_code, exc.detail)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return create_error_response(400, "Validation Error", exc.errors())

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return create_error_response(500, "Internal Server Error")

# Health Check endpoint
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "UP",
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

app.include_router(customer_router, prefix="/api/v1")
app.include_router(policy_router, prefix="/api/v1")
app.include_router(claims_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=(settings.environment == "development")
    )