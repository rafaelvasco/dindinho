"""Report service for generating transaction statistics and reports."""

import logging
from typing import Dict, List, Optional
from datetime import date, datetime
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, desc

from backend.models.transaction import Transaction, TransactionType
from backend.models.subscription import Subscription
from backend.models.category import Category

logger = logging.getLogger(__name__)


class ReportService:
    """
    Service for generating transaction reports and statistics.

    Provides various aggregations and analyses of transaction data.
    """

    def __init__(self, db: Session):
        """
        Initialize report service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def transactions_by_category(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[TransactionType] = None
    ) -> Dict[str, float]:
        """
        Get total transactions grouped by category.

        Args:
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)
            transaction_type: Filter by transaction type (optional)

        Returns:
            Dictionary mapping category to total amount
        """
        query = self.db.query(
            Category.name,
            func.sum(Transaction.amount).label('total')
        ).join(Category, Transaction.category_id == Category.id)

        # Apply date filters
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)

        # Apply transaction type filter
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)

        # Group by category
        results = query.group_by(Category.name).all()

        # Convert to dict
        category_totals = {category: float(total) for category, total in results}

        logger.info(f"Generated category report: {len(category_totals)} categories")
        return category_totals

    def transactions_by_month(
        self,
        year: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Get total transactions grouped by month.

        Args:
            year: Filter by year (optional, defaults to current year)

        Returns:
            Dictionary mapping "YYYY-MM" to total amount
        """
        if year is None:
            year = datetime.now().year

        query = self.db.query(
            extract('year', Transaction.date).label('year'),
            extract('month', Transaction.date).label('month'),
            func.sum(Transaction.amount).label('total')
        ).filter(
            extract('year', Transaction.date) == year
        ).group_by(
            extract('year', Transaction.date),
            extract('month', Transaction.date)
        ).order_by(
            extract('month', Transaction.date)
        )

        results = query.all()

        # Convert to dict with "YYYY-MM" format
        month_totals = {}
        for year_val, month_val, total in results:
            key = f"{int(year_val)}-{int(month_val):02d}"
            month_totals[key] = float(total)

        logger.info(f"Generated monthly report for {year}: {len(month_totals)} months")
        return month_totals

    def biggest_transactions(
        self,
        limit: int = 10,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[TransactionType] = None
    ) -> List[Transaction]:
        """
        Get the biggest transactions overall.

        Args:
            limit: Maximum number of results (default: 10)
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)
            transaction_type: Filter by transaction type (optional)

        Returns:
            List of transactions sorted by amount (descending)
        """
        query = self.db.query(Transaction)

        # Apply date filters
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)

        # Apply transaction type filter
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)

        # Order by amount descending and limit
        # Note: Amounts are already absolute values, no need for abs()
        transactions = query.order_by(desc(Transaction.amount)).limit(limit).all()

        logger.info(f"Found {len(transactions)} biggest transactions")
        return transactions

    def biggest_transactions_by_category(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Transaction]:
        """
        Get the biggest transaction for each category.

        Args:
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)

        Returns:
            Dictionary mapping category to biggest transaction
        """
        query = self.db.query(Transaction)

        # Apply date filters
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)

        all_transactions = query.all()

        # Group by category and find max
        category_max: Dict[str, Transaction] = {}
        for transaction in all_transactions:
            category = transaction.category.name if transaction.category else "Unknown"
            # Amounts are already absolute values, compare directly
            if category not in category_max or transaction.amount > category_max[category].amount:
                category_max[category] = transaction

        logger.info(f"Found biggest transactions for {len(category_max)} categories")
        return category_max

    def subscription_summary(self) -> List[Dict]:
        """
        Get summary of all subscriptions with current and historical values.

        Returns:
            List of subscription summaries
        """
        subscriptions = self.db.query(Subscription).order_by(Subscription.name).all()

        summaries = []
        for sub in subscriptions:
            # Get transaction count
            transaction_count = len(sub.transactions)

            # Get date range
            dates = [txn.date for txn in sub.transactions]
            first_date = min(dates) if dates else None
            last_date = max(dates) if dates else None

            # Calculate average value
            if sub.transactions:
                avg_value = sum(txn.amount for txn in sub.transactions) / len(sub.transactions)
            else:
                avg_value = 0.0

            summary = {
                "id": sub.id,
                "name": sub.name,
                "description": sub.description,
                "is_active": sub.is_active,
                "current_value": sub.current_value,
                "currency": sub.currency,
                "transaction_count": transaction_count,
                "first_date": first_date.isoformat() if first_date else None,
                "last_date": last_date.isoformat() if last_date else None,
                "average_value": avg_value,
                "historical_values": [
                    {"date": d.isoformat(), "amount": a}
                    for d, a in sub.historical_values
                ]
            }
            summaries.append(summary)

        logger.info(f"Generated subscription summary for {len(summaries)} subscriptions")
        return summaries

    def transaction_statistics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[TransactionType] = None
    ) -> Dict:
        """
        Get overall transaction statistics.

        Args:
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)
            transaction_type: Filter by transaction type (optional)

        Returns:
            Dictionary with various statistics
        """
        query = self.db.query(Transaction)

        # Apply date filters
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)

        # Apply transaction type filter
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)

        transactions = query.all()

        if not transactions:
            return {
                "total_transactions": 0,
                "total_amount": 0.0,
                "average_amount": 0.0,
                "min_amount": 0.0,
                "max_amount": 0.0,
                "category_count": 0,
                "date_range": {
                    "start": None,
                    "end": None
                }
            }

        amounts = [txn.amount for txn in transactions]
        dates = [txn.date for txn in transactions]
        categories = set(txn.category.name if txn.category else "Unknown" for txn in transactions)

        stats = {
            "total_transactions": len(transactions),
            "total_amount": sum(amounts),
            "average_amount": sum(amounts) / len(amounts),
            "min_amount": min(amounts),
            "max_amount": max(amounts),
            "category_count": len(categories),
            "date_range": {
                "start": min(dates).isoformat(),
                "end": max(dates).isoformat()
            }
        }

        logger.info(f"Generated statistics for {len(transactions)} transactions")
        return stats

    def monthly_comparison(
        self,
        year: int,
        category: Optional[str] = None
    ) -> Dict[str, Dict]:
        """
        Compare transactions month-over-month for a given year.

        Args:
            year: Year to analyze
            category: Filter by category (optional)

        Returns:
            Dictionary with monthly data and comparisons
        """
        query = self.db.query(
            extract('month', Transaction.date).label('month'),
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count'),
            func.avg(Transaction.amount).label('average')
        ).filter(
            extract('year', Transaction.date) == year
        )

        # Apply category filter
        if category:
            query = query.join(Category, Transaction.category_id == Category.id).filter(Category.name == category)

        results = query.group_by(
            extract('month', Transaction.date)
        ).order_by(
            extract('month', Transaction.date)
        ).all()

        # Build monthly comparison
        monthly_data = {}
        previous_total = None

        for month, total, count, average in results:
            month_key = f"{year}-{int(month):02d}"

            # Calculate change from previous month
            change_amount = None
            change_percent = None
            if previous_total is not None and previous_total > 0:
                change_amount = float(total) - previous_total
                change_percent = (change_amount / previous_total) * 100

            monthly_data[month_key] = {
                "total": float(total),
                "count": int(count),
                "average": float(average),
                "change_amount": change_amount,
                "change_percent": change_percent
            }

            previous_total = float(total)

        logger.info(f"Generated monthly comparison for {year}: {len(monthly_data)} months")
        return monthly_data
