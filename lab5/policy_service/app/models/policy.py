from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    policy_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # coverage_amount — the insured sum (e.g. 100 000 USD)
    coverage_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # premium_amount — the fee the customer pays
    premium_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Possible statuses:
    #   PENDING   — created by saga, waiting for payment confirmation
    #   ACTIVE    — payment confirmed, policy is active
    #   CANCELLED — saga compensated, policy was rolled back
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
