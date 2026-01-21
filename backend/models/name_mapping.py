"""Name mapping model for fuzzy matching and auto-renaming expense descriptions."""

from sqlalchemy import Column, Integer, String, DateTime, Float
from datetime import datetime

from backend.database import Base


class NameMapping(Base):
    """
    Model for storing fuzzy name mappings for expense descriptions.

    When a user renames an expense during import, the original pattern
    is stored along with the mapped name. Future expenses that fuzzy match
    the pattern will get a suggestion to use the mapped name.
    """

    __tablename__ = "name_mappings"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Original pattern from expense description
    pattern = Column(String, nullable=False, index=True)

    # Mapped/renamed value
    mapped_name = Column(String, nullable=False, index=True)

    # Fuzzy matching threshold (0-100)
    fuzzy_threshold = Column(Float, default=70.0, nullable=False)

    # How many times this mapping has been used
    usage_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        """String representation of the name mapping."""
        return f"<NameMapping(id={self.id}, pattern='{self.pattern}', mapped_name='{self.mapped_name}')>"

    def to_dict(self) -> dict:
        """Convert name mapping to dictionary."""
        return {
            "id": self.id,
            "pattern": self.pattern,
            "mapped_name": self.mapped_name,
            "fuzzy_threshold": self.fuzzy_threshold,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
