from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional

@dataclass
class Customer:
    id: str
    first_name: str
    last_name: str
    email: str

class CustomerRepository(ABC):
    @abstractmethod
    def save(self, customer: Customer) -> None: pass

    @abstractmethod
    def get_by_id(self, customer_id: str) -> Optional[Customer]: pass