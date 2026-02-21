from fastapi import FastAPI
from customer_management.api import router as customer_router
from policy_management.api import router as policy_router
from claims_management.api import router as claims_router

app = FastAPI(title="Insurance Platform Modular Monolith")

app.include_router(customer_router, prefix="/api/v1")
app.include_router(policy_router, prefix="/api/v1")
app.include_router(claims_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)