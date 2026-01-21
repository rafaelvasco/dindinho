"""Income source service for managing expected recurring income."""

import logging
from typing import List, Optional, Dict
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, extract

from backend.models.income_source import IncomeSource, IncomeSourceHistory
from backend.models.transaction import Transaction, TransactionType

logger = logging.getLogger(__name__)


class IncomeSourceService:
    """
    Service for income source operations.

    Handles:
    - CRUD operations for income sources
    - Historical tracking of expected amount changes
    - Linking income transactions to sources
    - Dashboard summary calculations
    """

    def __init__(self, db: Session):
        """
        Initialize income source service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_income_source(
        self,
        name: str,
        initial_expected_amount: float,
        cnpj: Optional[str] = None,
        description: Optional[str] = None
    ) -> IncomeSource:
        """
        Create a new income source with initial history entry.

        Args:
            name: Income source name (must be unique)
            initial_expected_amount: Initial expected monthly amount
            cnpj: Optional Brazilian CNPJ (14 digits)
            description: Optional description

        Returns:
            Created income source

        Raises:
            ValueError: If income source with this name already exists or amount is negative
        """
        # Check if income source with this name exists
        existing = self.db.query(IncomeSource).filter(
            IncomeSource.name == name
        ).first()

        if existing:
            raise ValueError(f"Income source with name '{name}' already exists")

        if initial_expected_amount < 0:
            raise ValueError("Expected amount must be >= 0")

        # Create income source
        income_source = IncomeSource(
            name=name,
            cnpj=cnpj,
            description=description,
            current_expected_amount=initial_expected_amount,
            is_active=True
        )

        self.db.add(income_source)
        self.db.flush()  # Flush to get ID for history entry

        # Create initial history entry
        history_entry = IncomeSourceHistory(
            income_source_id=income_source.id,
            expected_amount=initial_expected_amount,
            effective_date=datetime.utcnow(),
            note="Initial expected amount"
        )

        self.db.add(history_entry)
        self.db.commit()
        self.db.refresh(income_source)

        logger.info(f"Created income source: {name} with expected amount {initial_expected_amount}")
        return income_source

    def get_income_source(self, income_source_id: int) -> Optional[IncomeSource]:
        """
        Get income source by ID.

        Args:
            income_source_id: Income source ID

        Returns:
            Income source or None if not found
        """
        return self.db.query(IncomeSource).filter(
            IncomeSource.id == income_source_id
        ).first()

    def get_all_income_sources(
        self,
        active_only: bool = False
    ) -> List[IncomeSource]:
        """
        Get all income sources.

        Args:
            active_only: If True, only return active income sources

        Returns:
            List of income sources
        """
        query = self.db.query(IncomeSource)

        if active_only:
            query = query.filter(IncomeSource.is_active == True)

        return query.order_by(IncomeSource.name).all()

    def update_income_source(
        self,
        income_source_id: int,
        name: Optional[str] = None,
        cnpj: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[IncomeSource]:
        """
        Update income source metadata (not expected amount).

        To update expected amount, use update_expected_amount() method.

        Args:
            income_source_id: Income source ID
            name: New name (optional)
            cnpj: New CNPJ (optional)
            description: New description (optional)
            is_active: New active status (optional)

        Returns:
            Updated income source or None if not found

        Raises:
            ValueError: If name conflicts with existing income source
        """
        income_source = self.get_income_source(income_source_id)

        if not income_source:
            return None

        # Check for name conflict
        if name is not None and name != income_source.name:
            existing = self.db.query(IncomeSource).filter(
                IncomeSource.name == name,
                IncomeSource.id != income_source_id
            ).first()
            if existing:
                raise ValueError(f"Income source with name '{name}' already exists")

        if name is not None:
            income_source.name = name
        if cnpj is not None:
            income_source.cnpj = cnpj
        if description is not None:
            income_source.description = description
        if is_active is not None:
            income_source.is_active = is_active

        self.db.commit()
        self.db.refresh(income_source)

        logger.info(f"Updated income source {income_source_id}")
        return income_source

    def update_expected_amount(
        self,
        income_source_id: int,
        new_amount: float,
        note: Optional[str] = None
    ) -> Optional[IncomeSource]:
        """
        Update expected amount and create history entry.

        Args:
            income_source_id: Income source ID
            new_amount: New expected monthly amount
            note: Optional note explaining the change

        Returns:
            Updated income source or None if not found

        Raises:
            ValueError: If amount is negative
        """
        income_source = self.get_income_source(income_source_id)

        if not income_source:
            return None

        if new_amount < 0:
            raise ValueError("Expected amount must be >= 0")

        # Update current expected amount
        income_source.current_expected_amount = new_amount

        # Create history entry
        history_entry = IncomeSourceHistory(
            income_source_id=income_source_id,
            expected_amount=new_amount,
            effective_date=datetime.utcnow(),
            note=note
        )

        self.db.add(history_entry)
        self.db.commit()
        self.db.refresh(income_source)

        logger.info(f"Updated expected amount for income source {income_source_id} to {new_amount}")
        return income_source

    def delete_income_source(self, income_source_id: int) -> bool:
        """
        Delete an income source.

        This will unlink all associated transactions but not delete them.
        History entries are cascade deleted.

        Args:
            income_source_id: Income source ID

        Returns:
            True if deleted, False if not found
        """
        income_source = self.get_income_source(income_source_id)

        if not income_source:
            return False

        # Unlink all transactions
        for transaction in income_source.transactions:
            transaction.income_source_id = None

        self.db.delete(income_source)
        self.db.commit()

        logger.info(f"Deleted income source {income_source_id}")
        return True

    def link_transaction_to_income_source(
        self,
        transaction_id: int,
        income_source_id: int
    ) -> Transaction:
        """
        Link a transaction to an income source.

        Args:
            transaction_id: Transaction ID
            income_source_id: Income source ID

        Returns:
            Updated transaction

        Raises:
            ValueError: If transaction or income source not found, or if transaction is not INCOME type
        """
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        income_source = self.get_income_source(income_source_id)

        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        if not income_source:
            raise ValueError(f"Income source {income_source_id} not found")

        # Validate transaction type
        if transaction.transaction_type != TransactionType.INCOME:
            raise ValueError(
                f"Only INCOME transactions can be linked to income sources. "
                f"This transaction is type {transaction.transaction_type.value}"
            )

        # Link transaction to income source
        transaction.income_source_id = income_source_id

        self.db.commit()
        self.db.refresh(transaction)

        logger.info(f"Linked transaction {transaction_id} to income source {income_source_id}")
        return transaction

    def unlink_transaction_from_income_source(self, transaction_id: int) -> Optional[Transaction]:
        """
        Unlink a transaction from its income source.

        Args:
            transaction_id: Transaction ID

        Returns:
            Updated transaction or None if not found
        """
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()

        if not transaction:
            return None

        transaction.income_source_id = None

        self.db.commit()
        self.db.refresh(transaction)

        logger.info(f"Unlinked transaction {transaction_id} from income source")
        return transaction

    def get_expected_income_for_month(self, year: int, month: int) -> float:
        """
        Get total expected income for a specific month from all active sources.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Total expected income
        """
        active_sources = self.get_all_income_sources(active_only=True)

        total = 0.0
        for source in active_sources:
            total += source.get_expected_for_month(year, month)

        return total

    def get_actual_income_for_month(
        self,
        year: int,
        month: int,
        income_source_id: Optional[int] = None
    ) -> float:
        """
        Get total actual income received for a specific month.

        Args:
            year: Year
            month: Month (1-12)
            income_source_id: Optional income source ID to filter by

        Returns:
            Total actual income
        """
        query = self.db.query(Transaction).filter(
            Transaction.transaction_type == TransactionType.INCOME,
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month
        )

        if income_source_id is not None:
            query = query.filter(Transaction.income_source_id == income_source_id)
        else:
            # Only count transactions linked to income sources
            query = query.filter(Transaction.income_source_id.isnot(None))

        transactions = query.all()
        return sum(t.amount for t in transactions)

    def get_expected_income_summary(self, year: int, month: int) -> Dict:
        """
        Get expected income summary for dashboard display.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Dictionary with expected_total, actual_total, and sources list
        """
        active_sources = self.get_all_income_sources(active_only=True)

        sources_detail = []
        expected_total = 0.0
        actual_total = 0.0

        for source in active_sources:
            expected_amount = source.get_expected_for_month(year, month)
            actual_amount = self.get_actual_income_for_month(year, month, source.id)

            expected_total += expected_amount
            actual_total += actual_amount

            sources_detail.append({
                "id": source.id,
                "name": source.name,
                "expected_amount": expected_amount,
                "actual_amount": actual_amount
            })

        return {
            "expected_total": expected_total,
            "actual_total": actual_total,
            "sources": sources_detail
        }

    def get_income_source_history(
        self,
        income_source_id: int
    ) -> Optional[List[IncomeSourceHistory]]:
        """
        Get historical expected amount changes for an income source.

        Args:
            income_source_id: Income source ID

        Returns:
            List of history entries or None if income source not found
        """
        income_source = self.get_income_source(income_source_id)

        if not income_source:
            return None

        return self.db.query(IncomeSourceHistory).filter(
            IncomeSourceHistory.income_source_id == income_source_id
        ).order_by(IncomeSourceHistory.effective_date.desc()).all()
