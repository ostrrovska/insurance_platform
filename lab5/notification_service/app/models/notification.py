from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Unique event_id ensures idempotent processing (no duplicate notifications)
    event_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    routing_key: Mapped[str] = mapped_column(String(200), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
