"""Transaction category definitions for Brazilian financial transactions."""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from backend.database import Base


class TransactionCategory(str, Enum):
    """Brazilian transaction categories for classification."""

    GROCERIES = "Supermercado"
    RESTAURANTS = "Restaurantes"
    TRANSPORT = "Transporte"
    SUBSCRIPTIONS = "Assinaturas"
    UTILITIES = "Utilidades"
    HEALTHCARE = "Saúde"
    ENTERTAINMENT = "Entretenimento"
    SHOPPING = "Compras"
    EDUCATION = "Educação"
    HOUSING = "Moradia"
    INSURANCE = "Seguros"
    INVESTMENTS = "Investimentos"
    TAXES = "Impostos"
    TRANSFERS = "Transferências"
    OTHER = "Outros"

    @classmethod
    def get_all_categories(cls) -> list[str]:
        """Get all category values as a list."""
        return [category.value for category in cls]

    @classmethod
    def from_string(cls, value: str) -> "TransactionCategory":
        """
        Convert a string to TransactionCategory.

        Args:
            value: Category string value

        Returns:
            TransactionCategory enum member

        Raises:
            ValueError: If value is not a valid category
        """
        for category in cls:
            if category.value == value:
                return category
        raise ValueError(f"'{value}' is not a valid TransactionCategory")


class Category(Base):
    """Category model for transaction categorization with fuzzy matching support."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"
