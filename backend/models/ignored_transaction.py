"""Ignored transaction model for storing transaction descriptions to skip during import."""

from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional

from backend.database import Base


class IgnoredTransaction(Base):
    """
    Model for storing transaction descriptions that should be ignored during import.

    When a user marks a transaction to be ignored for all future imports,
    the description is stored here. During CSV import, transactions are checked
    against this list and skipped if they match (exact or fuzzy).
    """

    __tablename__ = "ignored_transactions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Transaction description to ignore (must be unique)
    description: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)

    # Fuzzy matching threshold (0-100). If None, use exact matching only.
    fuzzy_threshold: Mapped[Optional[float]] = mapped_column(Float, default=70.0, nullable=True)

    # How many times this ignore rule has been used
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        """String representation of the ignored transaction."""
        threshold_str = f", threshold={self.fuzzy_threshold}" if self.fuzzy_threshold else " (exact)"
        return f"<IgnoredTransaction(id={self.id}, description='{self.description}'{threshold_str})>"

    def to_dict(self) -> dict:
        """Convert ignored transaction to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "fuzzy_threshold": self.fuzzy_threshold,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
