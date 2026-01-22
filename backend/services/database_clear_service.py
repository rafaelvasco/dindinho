"""Service for clearing database data."""

from typing import Dict
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.models.transaction import Transaction
from backend.models.category import Category
from backend.models.subscription import Subscription
from backend.models.income_source import IncomeSource, IncomeSourceHistory
from backend.models.ignored_transaction import IgnoredTransaction
from backend.models.name_mapping import NameMapping


class DatabaseClearService:
    """Service to handle database clearing operations."""

    @staticmethod
    def clear_all_data(db: Session) -> Dict[str, int]:
        """
        Clear all data from the database.

        Deletes all records from all tables while preserving the schema.
        Categories are re-seeded after clearing.

        Args:
            db: Database session

        Returns:
            Dict mapping table names to number of records deleted

        Raises:
            Exception: If clearing fails
        """
        records_deleted = {}

        try:
            # Delete in order (respecting foreign key constraints)
            # Children first, then parents

            # 1. Transactions (references categories, subscriptions, income sources)
            count = db.query(Transaction).count()
            db.query(Transaction).delete()
            records_deleted["transactions"] = count

            # 2. Income Source History (references income sources)
            count = db.query(IncomeSourceHistory).count()
            db.query(IncomeSourceHistory).delete()
            records_deleted["income_source_history"] = count

            # 3. Independent tables (no foreign keys pointing to them from other tables)
            count = db.query(Subscription).count()
            db.query(Subscription).delete()
            records_deleted["subscriptions"] = count

            count = db.query(IncomeSource).count()
            db.query(IncomeSource).delete()
            records_deleted["income_sources"] = count

            count = db.query(IgnoredTransaction).count()
            db.query(IgnoredTransaction).delete()
            records_deleted["ignored_transactions"] = count

            count = db.query(NameMapping).count()
            db.query(NameMapping).delete()
            records_deleted["name_mappings"] = count

            # 4. Categories (last, as transactions reference them)
            count = db.query(Category).count()
            db.query(Category).delete()
            records_deleted["categories"] = count

            # Reset auto-increment sequences (SQLite specific)
            db.execute(text("DELETE FROM sqlite_sequence"))

            # Commit all deletions
            db.commit()

            # Re-seed initial categories
            from backend.services.category_service import CategoryService
            category_service = CategoryService(db)
            category_service.seed_initial_categories()

            return records_deleted

        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to clear database: {str(e)}")
