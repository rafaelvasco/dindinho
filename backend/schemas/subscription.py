"""Pydantic schemas for subscription API endpoints."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class HistoricalValue(BaseModel):
    """Schema for a single historical value point."""

    date: str = Field(..., description="Date in ISO format")
    amount: float = Field(..., description="Amount at this date")


class SubscriptionBase(BaseModel):
    """Base subscription schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Subscription name")
    description: Optional[str] = Field(None, description="Subscription description")
    pattern: Optional[str] = Field(None, min_length=1, description="Exact description pattern for matching")


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a new subscription."""

    initial_value: float = Field(default=0.0, description="Initial value")


class SubscriptionUpdate(BaseModel):
    """Schema for updating an existing subscription."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Subscription name")
    description: Optional[str] = Field(None, description="Subscription description")
    pattern: Optional[str] = Field(None, min_length=1, description="Exact description pattern")
    is_active: Optional[bool] = Field(None, description="Active status")


class SubscriptionResponse(SubscriptionBase):
    """Schema for subscription API responses."""

    id: int
    is_active: bool
    current_value: float
    currency: str
    created_at: datetime
    updated_at: datetime
    historical_values: List[HistoricalValue] = Field(default_factory=list)

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    """Schema for subscription list responses."""

    total: int = Field(..., description="Total number of subscriptions")
    subscriptions: List[SubscriptionResponse] = Field(..., description="List of subscriptions")


class SubscriptionSummary(BaseModel):
    """Schema for subscription summary with statistics."""

    id: int
    name: str
    description: Optional[str]
    is_active: bool
    current_value: float
    currency: str
    transaction_count: int = Field(..., description="Number of linked transactions")
    first_date: Optional[str] = Field(None, description="Date of first transaction")
    last_date: Optional[str] = Field(None, description="Date of last transaction")
    average_value: float = Field(..., description="Average transaction value")
    historical_values: List[HistoricalValue] = Field(default_factory=list)


class LinkTransactionRequest(BaseModel):
    """Schema for linking a transaction to a subscription."""

    transaction_id: int = Field(..., description="Transaction ID to link")
    subscription_id: int = Field(..., description="Subscription ID to link to")
