"""Pydantic schemas for report API endpoints."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import date


class CategoryTotal(BaseModel):
    """Schema for category total."""

    category: str = Field(..., description="Category name")
    total: float = Field(..., description="Total amount")


class TransactionsByCategoryResponse(BaseModel):
    """Schema for transactions by category report."""

    start_date: Optional[str] = Field(None, description="Start date filter (ISO format)")
    end_date: Optional[str] = Field(None, description="End date filter (ISO format)")
    categories: List[CategoryTotal] = Field(..., description="List of category totals")
    total_amount: float = Field(..., description="Total across all categories")


class MonthTotal(BaseModel):
    """Schema for monthly total."""

    month: str = Field(..., description="Month in YYYY-MM format")
    total: float = Field(..., description="Total amount for the month")


class TransactionsByMonthResponse(BaseModel):
    """Schema for transactions by month report."""

    year: int = Field(..., description="Year for the report")
    months: List[MonthTotal] = Field(..., description="List of monthly totals")
    total_amount: float = Field(..., description="Total across all months")


class BiggestTransactionItem(BaseModel):
    """Schema for a single biggest transaction item."""

    id: int
    date: str = Field(..., description="Transaction date (ISO format)")
    description: str
    amount: float
    category: str
    transaction_type: Optional[str] = None


class BiggestTransactionsResponse(BaseModel):
    """Schema for biggest transactions report."""

    limit: int = Field(..., description="Maximum number of results")
    transactions: List[BiggestTransactionItem] = Field(..., description="List of biggest transactions")


class BiggestTransactionByCategory(BaseModel):
    """Schema for biggest transaction in a category."""

    category: str
    transaction: BiggestTransactionItem


class BiggestTransactionsByCategoryResponse(BaseModel):
    """Schema for biggest transactions by category report."""

    categories: List[BiggestTransactionByCategory] = Field(..., description="Biggest transaction per category")


class DateRange(BaseModel):
    """Schema for date range."""

    start: Optional[str] = Field(None, description="Start date (ISO format)")
    end: Optional[str] = Field(None, description="End date (ISO format)")


class TransactionStatistics(BaseModel):
    """Schema for transaction statistics."""

    total_transactions: int = Field(..., description="Total number of transactions")
    total_amount: float = Field(..., description="Total amount")
    average_amount: float = Field(..., description="Average transaction amount")
    min_amount: float = Field(..., description="Minimum transaction amount")
    max_amount: float = Field(..., description="Maximum transaction amount")
    category_count: int = Field(..., description="Number of different categories")
    date_range: DateRange = Field(..., description="Date range of transactions")


class MonthlyComparison(BaseModel):
    """Schema for monthly comparison data."""

    month: str = Field(..., description="Month in YYYY-MM format")
    total: float = Field(..., description="Total amount")
    count: int = Field(..., description="Number of transactions")
    average: float = Field(..., description="Average transaction amount")
    change_amount: Optional[float] = Field(None, description="Change from previous month")
    change_percent: Optional[float] = Field(None, description="Percent change from previous month")


class MonthlyComparisonResponse(BaseModel):
    """Schema for monthly comparison report."""

    year: int = Field(..., description="Year for the report")
    category: Optional[str] = Field(None, description="Category filter (if any)")
    months: List[MonthlyComparison] = Field(..., description="Monthly comparison data")
