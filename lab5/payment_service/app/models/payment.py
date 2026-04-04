from datetime import datetime, timezone

from sqlalchemy import Integer, Float, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Which policy and customer this payment belongs to
    policy_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # The premium amount being charged
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    # Payment lifecycle statuses:
    #   COMPLETED — money was successfully charged
    #   REFUNDED  — compensation transaction: money was returned (saga rollback)
    #   FAILED    — payment was attempted but failed (e.g. simulate_failure=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="COMPLETED")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
