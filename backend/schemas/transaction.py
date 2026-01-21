"""Pydantic schemas for transaction API endpoints."""

from pydantic import BaseModel, Field
from datetime import date as DateType, datetime
from typing import Optional, Literal


class TransactionBase(BaseModel):
    """Base transaction schema with common fields."""

    date: DateType = Field(..., description="Transaction date")
    description: str = Field(..., min_length=1, description="Transaction description")
    amount: float = Field(..., ge=0, description="Transaction amount (always positive/absolute value)")
    currency: str = Field(default="BRL", description="Currency code")
    transaction_type: Literal['EXPENSE', 'INCOME', 'PAYMENT', 'REFUND'] = Field(..., description="Transaction type: EXPENSE (spending), INCOME (receiving), PAYMENT (debt/transfer), REFUND (credits)")
    original_category: Optional[str] = Field(None, description="Original category from CSV")


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""

    category: str = Field(..., description="Transaction category name")
    source_type: str = Field(..., description="Source type: 'credit_card' or 'account_extract'")
    source_file: Optional[str] = Field(None, description="Source CSV filename")
    raw_data: Optional[str] = Field(None, description="Raw CSV row as JSON")
    subscription_id: Optional[int] = Field(None, description="Linked subscription ID")


class TransactionUpdate(BaseModel):
    """Schema for updating an existing transaction."""

    category: Optional[str] = Field(None, description="Transaction category name")
    description: Optional[str] = Field(None, min_length=1, description="Transaction description")
    subscription_id: Optional[int] = Field(None, description="Linked subscription ID")
    income_source_id: Optional[int] = Field(None, description="Linked income source ID")


class TransactionResponse(TransactionBase):
    """Schema for transaction API responses."""

    id: int
    category: str
    category_id: int
    source_type: str
    source_file: Optional[str] = None
    subscription_id: Optional[int] = None
    income_source_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """Schema for paginated transaction list responses."""

    total: int = Field(..., description="Total number of transactions")
    transactions: list[TransactionResponse] = Field(..., description="List of transactions")


class TransactionFilter(BaseModel):
    """Schema for filtering transactions."""

    start_date: Optional[DateType] = Field(None, description="Filter by start date")
    end_date: Optional[DateType] = Field(None, description="Filter by end date")
    category: Optional[str] = Field(None, description="Filter by category")
    min_amount: Optional[float] = Field(None, ge=0, description="Filter by minimum amount")
    max_amount: Optional[float] = Field(None, ge=0, description="Filter by maximum amount")
    search: Optional[str] = Field(None, description="Search in description")
    source_type: Optional[str] = Field(None, description="Filter by source type")
    subscription_id: Optional[int] = Field(None, description="Filter by subscription ID")
    income_source_id: Optional[int] = Field(None, description="Filter by income source ID")
    transaction_type: Optional[Literal['EXPENSE', 'INCOME', 'PAYMENT', 'REFUND']] = Field(None, description="Filter by transaction type")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
