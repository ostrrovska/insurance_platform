"""
Saga state model.

The orchestrator persists each saga's current state so that:
  1. We can track progress and diagnose failures.
  2. We have a durable record of which compensating transactions to run.
  3. The saga is observable via GET /api/v1/sagas/{id}.

Saga lifecycle (Policy Purchase):
  STARTED
    → VALIDATING_CUSTOMER
    → CREATING_POLICY
    → PROCESSING_PAYMENT
    → ACTIVATING_POLICY
    → COMPLETED          ← happy path

  If any step fails:
    → COMPENSATING       ← running rollback steps
    → COMPENSATED        ← rollback done, data is consistent again

  FAILED is used only when compensation itself fails (rare).
"""

import json
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Saga(Base):
    __tablename__ = "sagas"

    # UUID string as primary key — easier to share with clients
    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)

    saga_type: Mapped[str] = mapped_column(String(100), nullable=False, default="POLICY_PURCHASE")

    # Current saga status — updated at every step
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="STARTED")

    # Input data
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_type: Mapped[str] = mapped_column(String(100), nullable=False)
    coverage_amount: Mapped[float] = mapped_column(Float, nullable=False)
    premium_amount: Mapped[float] = mapped_column(Float, nullable=False)

    # IDs of resources created during the saga.
    # Needed by compensating transactions to know what to roll back.
    policy_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Human-readable error message when status is COMPENSATED or FAILED
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON log of every step with timestamp — useful for debugging
    steps_log: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def append_step(self, step: str, details: str = "") -> None:
        """Add a step entry to the steps_log JSON array."""
        steps = json.loads(self.steps_log)
        steps.append({
            "step": step,
            "details": details,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        self.steps_log = json.dumps(steps)
