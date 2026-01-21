"""Pydantic schemas for income source API endpoints."""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List
import re


class HistoryEntry(BaseModel):
    """Schema for a single history entry."""

    date: str = Field(..., description="Effective date in ISO format")
    amount: float = Field(..., description="Expected amount at this date")
    note: Optional[str] = Field(None, description="Note explaining the change")


class IncomeSourceBase(BaseModel):
    """Base income source schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Income source name")
    cnpj: Optional[str] = Field(None, description="Brazilian CNPJ (14 digits)")
    description: Optional[str] = Field(None, description="Income source description")

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj(cls, v: Optional[str]) -> Optional[str]:
        """Validate CNPJ format (14 digits, with or without formatting)."""
        if v is None:
            return None

        # Remove formatting characters
        cnpj_digits = re.sub(r"[^\d]", "", v)

        # Validate length
        if len(cnpj_digits) != 14:
            raise ValueError("CNPJ must have exactly 14 digits")

        return cnpj_digits


class IncomeSourceCreate(IncomeSourceBase):
    """Schema for creating a new income source."""

    initial_expected_amount: float = Field(..., ge=0, description="Initial expected monthly amount")


class IncomeSourceUpdate(BaseModel):
    """Schema for updating an existing income source."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Income source name")
    cnpj: Optional[str] = Field(None, description="Brazilian CNPJ (14 digits)")
    description: Optional[str] = Field(None, description="Income source description")
    is_active: Optional[bool] = Field(None, description="Active status")

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj(cls, v: Optional[str]) -> Optional[str]:
        """Validate CNPJ format (14 digits, with or without formatting)."""
        if v is None:
            return None

        # Remove formatting characters
        cnpj_digits = re.sub(r"[^\d]", "", v)

        # Validate length
        if len(cnpj_digits) != 14:
            raise ValueError("CNPJ must have exactly 14 digits")

        return cnpj_digits


class UpdateExpectedAmountRequest(BaseModel):
    """Schema for updating expected amount."""

    expected_amount: float = Field(..., ge=0, description="New expected monthly amount")
    note: Optional[str] = Field(None, description="Note explaining the change")


class IncomeSourceResponse(IncomeSourceBase):
    """Schema for income source API responses."""

    id: int
    is_active: bool
    current_expected_amount: float
    currency: str
    created_at: datetime
    updated_at: datetime
    historical_values: List[HistoryEntry] = Field(default_factory=list)

    class Config:
        from_attributes = True


class IncomeSourceListResponse(BaseModel):
    """Schema for income source list responses."""

    total: int = Field(..., description="Total number of income sources")
    income_sources: List[IncomeSourceResponse] = Field(..., description="List of income sources")


class IncomeSourceSummary(BaseModel):
    """Schema for income source summary with statistics."""

    id: int
    name: str
    description: Optional[str]
    cnpj: Optional[str]
    is_active: bool
    current_expected_amount: float
    currency: str
    transaction_count: int = Field(..., description="Number of linked transactions")
    first_date: Optional[str] = Field(None, description="Date of first transaction")
    last_date: Optional[str] = Field(None, description="Date of last transaction")
    total_received: float = Field(..., description="Total amount received from linked transactions")
    historical_values: List[HistoryEntry] = Field(default_factory=list)


class LinkTransactionRequest(BaseModel):
    """Schema for linking a transaction to an income source."""

    transaction_id: int = Field(..., description="Transaction ID to link")
    income_source_id: int = Field(..., description="Income source ID to link to")


class ExpectedIncomeSourceDetail(BaseModel):
    """Schema for a single income source in the dashboard summary."""

    id: int
    name: str
    expected_amount: float
    actual_amount: float


class ExpectedIncomeSummary(BaseModel):
    """Schema for expected income dashboard summary."""

    expected_total: float = Field(..., description="Total expected income for the month")
    actual_total: float = Field(..., description="Total actual income received for the month")
    sources: List[ExpectedIncomeSourceDetail] = Field(
        default_factory=list,
        description="Breakdown by income source"
    )
