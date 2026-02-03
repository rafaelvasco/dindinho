"""Transaction model for storing financial transactions."""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Index, CheckConstraint, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
import enum

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.category import Category
    from backend.models.subscription import Subscription
    from backend.models.income_source import IncomeSource


class TransactionType(enum.Enum):
    """Transaction type enum."""
    EXPENSE = "EXPENSE"  # Money spent on goods/services
    INCOME = "INCOME"    # Money received (salary, deposits)
    PAYMENT = "PAYMENT"  # Paying debts or moving money between accounts
    REFUND = "REFUND"    # Credits/refunds back


class Transaction(Base):
    """
    Transaction model representing a financial transaction.

    Stores transactions imported from CSV files with AI-inferred categorization.
    Amounts are always stored as absolute values, with transaction_type indicating direction.
    """

    __tablename__ = "transactions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Core transaction fields
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, default="BRL", nullable=False)

    # Categorization
    original_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Original from CSV (may be ignored)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    category: Mapped["Category"] = relationship("Category", back_populates="transactions")

    # Transaction type - indicates money flow direction
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType),
        nullable=False
    )  # EXPENSE (spending), INCOME (receiving), PAYMENT (debt/transfer), or REFUND

    # Source tracking
    source_file: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Which CSV file
    source_type: Mapped[str] = mapped_column(String, nullable=False)  # "credit_card" or "account_extract"
    raw_data: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # JSON of original CSV row for audit

    # Subscription relationship
    subscription_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("subscriptions.id"), nullable=True, index=True)
    subscription: Mapped[Optional["Subscription"]] = relationship("Subscription", back_populates="transactions")

    # Income source relationship
    income_source_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("income_sources.id"), nullable=True, index=True)
    income_source: Mapped[Optional["IncomeSource"]] = relationship("IncomeSource", back_populates="transactions")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Composite index for duplicate detection and amount constraint
    __table_args__ = (
        Index('idx_transaction_duplicate', 'date', 'description', 'amount'),
        CheckConstraint('amount >= 0', name='check_amount_positive'),
    )

    def __repr__(self) -> str:
        """String representation of the transaction."""
        return (
            f"<Transaction(id={self.id}, date={self.date}, "
            f"description='{self.description}', amount={self.amount} {self.currency}, "
            f"type={self.transaction_type.value if self.transaction_type else None})>"
        )

    def to_dict(self) -> dict:
        """Convert transaction to dictionary."""
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "description": self.description,
            "amount": self.amount,
            "currency": self.currency,
            "original_category": self.original_category,
            "category": self.category.name if self.category else None,
            "category_id": self.category_id,
            "transaction_type": self.transaction_type.value if self.transaction_type else None,
            "source_file": self.source_file,
            "source_type": self.source_type,
            "subscription_id": self.subscription_id,
            "income_source_id": self.income_source_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
