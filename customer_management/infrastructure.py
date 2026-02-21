from typing import Optional, Dict
from .domain import Customer, CustomerRepository

class InMemoryCustomerRepository(CustomerRepository):
    def __init__(self):
        self._db: Dict[str, Customer] = {}

    def save(self, customer: Customer) -> None:
        self._db[customer.id] = customer

    def get_by_id(self, customer_id: str) -> Optional[Customer]:
        return self._db.get(customer_id)