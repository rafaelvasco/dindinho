"""Subscription model for tracking recurring transactions."""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Tuple
from datetime import date

from backend.database import Base


class Subscription(Base):
    """
    Subscription model for tracking recurring transactions.

    Stores subscription information and links to associated transaction items.
    The current_value is denormalized for performance and updated when new
    transactions are linked.
    """

    __tablename__ = "subscriptions"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Subscription details
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Current value (denormalized for performance)
    current_value = Column(Float, nullable=False)
    currency = Column(String, default="BRL", nullable=False)

    # Pattern for auto-matching transactions (exact description match)
    pattern = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to transactions (ordered by date)
    transactions = relationship(
        "Transaction",
        back_populates="subscription",
        order_by="Transaction.date",
        cascade="all, delete-orphan"
    )

    @property
    def historical_values(self) -> List[Tuple[date, float]]:
        """
        Get historical values for this subscription.

        Returns list of (date, amount) tuples from all linked transactions,
        ordered by date.

        Returns:
            List of (date, amount) tuples
        """
        return [(txn.date, txn.amount) for txn in self.transactions]

    def __repr__(self) -> str:
        """String representation of the subscription."""
        status = "active" if self.is_active else "inactive"
        return (
            f"<Subscription(id={self.id}, name='{self.name}', "
            f"current_value={self.current_value} {self.currency}, status={status})>"
        )

    def to_dict(self) -> dict:
        """Convert subscription to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "current_value": self.current_value,
            "currency": self.currency,
            "pattern": self.pattern,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "historical_values": [
                {"date": d.isoformat(), "amount": a} for d, a in self.historical_values
            ],
        }
