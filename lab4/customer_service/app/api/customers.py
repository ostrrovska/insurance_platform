import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.customer import Customer
from app.outbox.writer import publish_event
from app.schemas.customer import CustomerCreate, CustomerResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/customers", tags=["Customers"])

EXCHANGE = "customers"


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(body: CustomerCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a customer AND atomically append a CustomerCreated event
    to the Outbox table — both in the same DB transaction.
    """
    # 1. Business operation
    customer = Customer(name=body.name, email=body.email)
    db.add(customer)
    await db.flush()  # assigns PK without committing

    # 2. Write event to outbox (same transaction!)
    await publish_event(
        db,
        event_type="CustomerCreated",
        exchange=EXCHANGE,
        routing_key="customers.created",
        payload={
            "customer_id": customer.id,
            "name": customer.name,
            "email": customer.email,
        },
    )

    # 3. Single commit — both customer row and outbox row land together
    await db.commit()
    await db.refresh(customer)

    logger.info("Created customer id=%d, outbox event queued.", customer.id)
    return customer


@router.get("/", response_model=list[CustomerResponse])
async def list_customers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).order_by(Customer.id))
    return result.scalars().all()


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer
