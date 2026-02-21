import uuid
from pydantic import BaseModel
from typing import Optional
from .domain import Customer, CustomerRepository

class CustomerDTO(BaseModel):
    id: Optional[str] = None
    first_name: str
    last_name: str
    email: str

class CustomerService:
    def __init__(self, repository: CustomerRepository):
        self.repository = repository

    def register_customer(self, dto: CustomerDTO) -> CustomerDTO:
        # Мапінг DTO -> Entity
        customer = Customer(
            id=str(uuid.uuid4()),
            first_name=dto.first_name,
            last_name=dto.last_name,
            email=dto.email
        )
        self.repository.save(customer)
        # Мапінг Entity -> DTO
        return CustomerDTO(id=customer.id, first_name=customer.first_name, last_name=customer.last_name, email=customer.email)

    def get_customer(self, customer_id: str) -> Optional[CustomerDTO]:
        customer = self.repository.get_by_id(customer_id)
        if customer:
            return CustomerDTO(id=customer.id, first_name=customer.first_name, last_name=customer.last_name, email=customer.email)
        return None