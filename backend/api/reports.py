"""API endpoints for transaction reports and statistics."""

import logging
from typing import Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.report_service import ReportService
from backend.models.transaction import TransactionType
from backend.schemas.report import (
    TransactionsByCategoryResponse,
    CategoryTotal,
    TransactionsByMonthResponse,
    MonthTotal,
    BiggestTransactionsResponse,
    BiggestTransactionItem,
    BiggestTransactionsByCategoryResponse,
    BiggestTransactionByCategory,
    TransactionStatistics,
    MonthlyComparisonResponse,
    MonthlyComparison
)
from backend.schemas.subscription import SubscriptionSummary
from backend.schemas.income_source import ExpectedIncomeSummary

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/by-category", response_model=TransactionsByCategoryResponse)
async def get_transactions_by_category(
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type (EXPENSE, INCOME, PAYMENT, REFUND)"),
    db: Session = Depends(get_db)
):
    """
    Get transactions grouped by category.

    Returns total amount for each category, optionally filtered by date range and transaction type.
    """
    report_service = ReportService(db)

    # Convert transaction_type string to enum
    txn_type = None
    if transaction_type:
        try:
            txn_type = TransactionType[transaction_type.upper()]
        except KeyError:
            pass

    category_totals = report_service.transactions_by_category(
        start_date=start_date,
        end_date=end_date,
        transaction_type=txn_type
    )

    # Convert to response format
    categories = [
        CategoryTotal(category=cat, total=total)
        for cat, total in category_totals.items()
    ]

    total_amount = sum(category_totals.values())

    return TransactionsByCategoryResponse(
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        categories=categories,
        total_amount=total_amount
    )


@router.get("/by-month", response_model=TransactionsByMonthResponse)
async def get_transactions_by_month(
    year: int = Query(default_factory=lambda: datetime.now().year, description="Year for report"),
    db: Session = Depends(get_db)
):
    """
    Get transactions grouped by month for a specific year.

    Returns total amount for each month.
    """
    report_service = ReportService(db)

    month_totals = report_service.transactions_by_month(year=year)

    # Convert to response format
    months = [
        MonthTotal(month=month, total=total)
        for month, total in month_totals.items()
    ]

    total_amount = sum(month_totals.values())

    return TransactionsByMonthResponse(
        year=year,
        months=months,
        total_amount=total_amount
    )


@router.get("/biggest-transactions", response_model=BiggestTransactionsResponse)
async def get_biggest_transactions(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type (EXPENSE, INCOME, PAYMENT, REFUND)"),
    db: Session = Depends(get_db)
):
    """
    Get the biggest transactions overall.

    Returns transactions sorted by amount (descending), optionally filtered by date range and transaction type.
    """
    report_service = ReportService(db)

    # Convert transaction_type string to enum
    txn_type = None
    if transaction_type:
        try:
            txn_type = TransactionType[transaction_type.upper()]
        except KeyError:
            pass

    transactions = report_service.biggest_transactions(
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        transaction_type=txn_type
    )

    # Convert to response format
    transaction_items = [
        BiggestTransactionItem(
            id=txn.id,
            date=txn.date.isoformat(),
            description=txn.description,
            amount=txn.amount,
            category=txn.category.name if txn.category else "Unknown",
            transaction_type=txn.transaction_type.value if txn.transaction_type else None
        )
        for txn in transactions
    ]

    return BiggestTransactionsResponse(
        limit=limit,
        transactions=transaction_items
    )


@router.get("/biggest-by-category", response_model=BiggestTransactionsByCategoryResponse)
async def get_biggest_transactions_by_category(
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    db: Session = Depends(get_db)
):
    """
    Get the biggest transaction for each category.

    Returns one transaction per category (the one with highest amount).
    """
    report_service = ReportService(db)

    category_max = report_service.biggest_transactions_by_category(
        start_date=start_date,
        end_date=end_date
    )

    # Convert to response format
    categories = [
        BiggestTransactionByCategory(
            category=cat,
            transaction=BiggestTransactionItem(
                id=txn.id,
                date=txn.date.isoformat(),
                description=txn.description,
                amount=txn.amount,
                category=txn.category.name if txn.category else "Unknown",
                transaction_type=txn.transaction_type.value if txn.transaction_type else None
            )
        )
        for cat, txn in category_max.items()
    ]

    return BiggestTransactionsByCategoryResponse(categories=categories)


@router.get("/statistics", response_model=TransactionStatistics)
async def get_transaction_statistics(
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type (EXPENSE, INCOME, PAYMENT, REFUND)"),
    db: Session = Depends(get_db)
):
    """
    Get overall transaction statistics.

    Returns aggregated statistics including total, average, min, max, etc.
    """
    report_service = ReportService(db)

    # Convert transaction_type string to enum
    txn_type = None
    if transaction_type:
        try:
            txn_type = TransactionType[transaction_type.upper()]
        except KeyError:
            pass

    stats = report_service.transaction_statistics(
        start_date=start_date,
        end_date=end_date,
        transaction_type=txn_type
    )

    return TransactionStatistics(**stats)


@router.get("/monthly-comparison", response_model=MonthlyComparisonResponse)
async def get_monthly_comparison(
    year: int = Query(default_factory=lambda: datetime.now().year, description="Year for comparison"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """
    Get month-over-month comparison for a specific year.

    Shows total, count, average, and change from previous month for each month.
    Optionally filter by category.
    """
    report_service = ReportService(db)

    monthly_data = report_service.monthly_comparison(
        year=year,
        category=category
    )

    # Convert to response format
    months = [
        MonthlyComparison(
            month=month,
            total=data['total'],
            count=data['count'],
            average=data['average'],
            change_amount=data['change_amount'],
            change_percent=data['change_percent']
        )
        for month, data in monthly_data.items()
    ]

    return MonthlyComparisonResponse(
        year=year,
        category=category,
        months=months
    )


@router.get("/subscriptions", response_model=list[SubscriptionSummary])
async def get_subscription_summary(db: Session = Depends(get_db)):
    """
    Get summary of all subscriptions with statistics.

    Returns subscription details, transaction counts, averages, and historical values.
    """
    report_service = ReportService(db)

    summaries = report_service.subscription_summary()

    return [SubscriptionSummary(**summary) for summary in summaries]


@router.get("/expected-income", response_model=ExpectedIncomeSummary)
async def get_expected_income(
    year: int = Query(default_factory=lambda: datetime.now().year, description="Year for report"),
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12, description="Month for report (1-12)"),
    db: Session = Depends(get_db)
):
    """
    Get expected income summary for dashboard display.

    Returns expected vs actual income for the specified month,
    with breakdown by income source.
    """
    from backend.services.income_source_service import IncomeSourceService

    income_source_service = IncomeSourceService(db)

    summary = income_source_service.get_expected_income_summary(year=year, month=month)

    return ExpectedIncomeSummary(**summary)
