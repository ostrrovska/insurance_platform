"""
Transactional Outbox table — same pattern as in customer_service.
Events are written atomically with business operations and published
to RabbitMQ by the relay background task.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OutboxStatus(str, PyEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    exchange: Mapped[str] = mapped_column(String(100), nullable=False)
    routing_key: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(OutboxStatus), default=OutboxStatus.PENDING, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
