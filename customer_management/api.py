from fastapi import APIRouter, HTTPException
from .application import CustomerService, CustomerDTO
from .infrastructure import InMemoryCustomerRepository
from core.schemas import ErrorResponse  # Імпортуємо нашу модель помилки

router = APIRouter(tags=["Customers"])
repo = InMemoryCustomerRepository()
service = CustomerService(repo)

@router.post(
    "/customers",
    response_model=CustomerDTO,
    responses={
        400: {"model": ErrorResponse, "description": "Validation Error"}
    }
)
def create_customer(customer_data: CustomerDTO):
    return service.register_customer(customer_data)

@router.get(
    "/customers/{customer_id}",
    response_model=CustomerDTO,
    responses={
        404: {"model": ErrorResponse, "description": "Customer not found"}
    }
)
def get_customer(customer_id: str):
    customer = service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer