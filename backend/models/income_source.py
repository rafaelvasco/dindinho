"""Income source model for tracking expected recurring income."""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Tuple, Optional
from datetime import date

from backend.database import Base


class IncomeSource(Base):
    """
    Income source model for tracking expected recurring income.

    Stores income source information and links to associated income transactions.
    The current_expected_amount is the latest expected monthly income amount.
    Historical changes to expected amounts are tracked in IncomeSourceHistory.
    """

    __tablename__ = "income_sources"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Income source details
    name = Column(String, nullable=False, unique=True, index=True)
    cnpj = Column(String, nullable=True)  # Brazilian tax ID (14 digits)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Current expected amount (denormalized for performance)
    current_expected_amount = Column(Float, nullable=False)
    currency = Column(String, default="BRL", nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    transactions = relationship(
        "Transaction",
        back_populates="income_source",
        order_by="Transaction.date"
    )
    history = relationship(
        "IncomeSourceHistory",
        back_populates="income_source",
        order_by="IncomeSourceHistory.effective_date.desc()",
        cascade="all, delete-orphan"
    )

    def get_expected_for_month(self, year: int, month: int) -> float:
        """
        Get expected amount for a specific month.

        Looks through history to find the expected amount that was active
        for the given month.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Expected amount for that month
        """
        target_date = datetime(year, month, 1)

        # Find the most recent history entry before or at the target date
        for hist in self.history:
            if hist.effective_date <= target_date:
                return hist.expected_amount

        # If no history found, return current expected amount
        return self.current_expected_amount

    @property
    def historical_values(self) -> List[Tuple[date, float]]:
        """
        Get historical expected amounts for this income source.

        Returns list of (effective_date, expected_amount) tuples from history,
        ordered by date descending.

        Returns:
            List of (date, amount) tuples
        """
        return [(hist.effective_date.date(), hist.expected_amount) for hist in self.history]

    def __repr__(self) -> str:
        """String representation of the income source."""
        status = "active" if self.is_active else "inactive"
        return (
            f"<IncomeSource(id={self.id}, name='{self.name}', "
            f"current_expected_amount={self.current_expected_amount} {self.currency}, "
            f"status={status})>"
        )

    def to_dict(self) -> dict:
        """Convert income source to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "cnpj": self.cnpj,
            "description": self.description,
            "is_active": self.is_active,
            "current_expected_amount": self.current_expected_amount,
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "historical_values": [
                {"date": d.isoformat(), "amount": a} for d, a in self.historical_values
            ],
        }


class IncomeSourceHistory(Base):
    """
    Historical tracking of expected amount changes for income sources.

    Each time an income source's expected amount is updated, a new history
    entry is created to track when and what changed.
    """

    __tablename__ = "income_source_history"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to income source
    income_source_id = Column(Integer, ForeignKey("income_sources.id"), nullable=False, index=True)

    # Historical data
    expected_amount = Column(Float, nullable=False)
    effective_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    note = Column(String, nullable=True)  # Optional note explaining the change

    # Relationship
    income_source = relationship("IncomeSource", back_populates="history")

    def __repr__(self) -> str:
        """String representation of the history entry."""
        return (
            f"<IncomeSourceHistory(id={self.id}, income_source_id={self.income_source_id}, "
            f"expected_amount={self.expected_amount}, effective_date={self.effective_date})>"
        )

    def to_dict(self) -> dict:
        """Convert history entry to dictionary."""
        return {
            "id": self.id,
            "income_source_id": self.income_source_id,
            "expected_amount": self.expected_amount,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "note": self.note,
        }
