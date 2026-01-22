"""Service for exporting database to JSON format."""

from datetime import datetime, date
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from decimal import Decimal

from backend.models.transaction import Transaction, TransactionType
from backend.models.category import Category
from backend.models.subscription import Subscription
from backend.models.income_source import IncomeSource, IncomeSourceHistory
from backend.models.ignored_transaction import IgnoredTransaction
from backend.models.name_mapping import NameMapping
from backend.schemas.database_export import DatabaseExport, ExportMetadata


class DatabaseExportService:
    """Service to handle database export operations."""

    EXPORT_VERSION = "1.0"
    SCHEMA_VERSION = "1"

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """
        Serialize a value to JSON-compatible format.

        Args:
            value: Value to serialize

        Returns:
            JSON-compatible value
        """
        if value is None:
            return None
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        elif isinstance(value, TransactionType):
            return value.value
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, (int, float, str, bool)):
            return value
        else:
            return str(value)

    @staticmethod
    def _serialize_model(model: Any) -> Dict[str, Any]:
        """
        Serialize a SQLAlchemy model to dictionary.

        Args:
            model: SQLAlchemy model instance

        Returns:
            Dictionary with serialized fields
        """
        result = {}
        for column in model.__table__.columns:
            value = getattr(model, column.name)
            result[column.name] = DatabaseExportService._serialize_value(value)
        return result

    @staticmethod
    def _serialize_categories(db: Session) -> List[Dict[str, Any]]:
        """Serialize all categories."""
        categories = db.query(Category).all()
        return [DatabaseExportService._serialize_model(cat) for cat in categories]

    @staticmethod
    def _serialize_subscriptions(db: Session) -> List[Dict[str, Any]]:
        """Serialize all subscriptions."""
        subscriptions = db.query(Subscription).all()
        return [DatabaseExportService._serialize_model(sub) for sub in subscriptions]

    @staticmethod
    def _serialize_income_sources(db: Session) -> List[Dict[str, Any]]:
        """Serialize all income sources."""
        income_sources = db.query(IncomeSource).all()
        return [DatabaseExportService._serialize_model(source) for source in income_sources]

    @staticmethod
    def _serialize_income_source_history(db: Session) -> List[Dict[str, Any]]:
        """Serialize all income source history."""
        history = db.query(IncomeSourceHistory).all()
        return [DatabaseExportService._serialize_model(hist) for hist in history]

    @staticmethod
    def _serialize_transactions(db: Session) -> List[Dict[str, Any]]:
        """Serialize all transactions."""
        transactions = db.query(Transaction).all()
        return [DatabaseExportService._serialize_model(txn) for txn in transactions]

    @staticmethod
    def _serialize_ignored_transactions(db: Session) -> List[Dict[str, Any]]:
        """Serialize all ignored transactions."""
        ignored = db.query(IgnoredTransaction).all()
        return [DatabaseExportService._serialize_model(ign) for ign in ignored]

    @staticmethod
    def _serialize_name_mappings(db: Session) -> List[Dict[str, Any]]:
        """Serialize all name mappings."""
        mappings = db.query(NameMapping).all()
        return [DatabaseExportService._serialize_model(mapping) for mapping in mappings]

    @staticmethod
    def _generate_metadata(db: Session, tables: Dict[str, List]) -> ExportMetadata:
        """
        Generate export metadata.

        Args:
            db: Database session
            tables: Dictionary of exported tables

        Returns:
            ExportMetadata with statistics
        """
        # Get date range from transactions
        date_range = None
        transactions = db.query(Transaction).order_by(Transaction.date).all()
        if transactions:
            date_range = {
                "start": transactions[0].date.isoformat(),
                "end": transactions[-1].date.isoformat()
            }

        return ExportMetadata(
            total_transactions=len(tables.get("transactions", [])),
            total_categories=len(tables.get("categories", [])),
            total_subscriptions=len(tables.get("subscriptions", [])),
            total_income_sources=len(tables.get("income_sources", [])),
            date_range=date_range
        )

    @staticmethod
    def export_to_json(db: Session) -> Dict[str, Any]:
        """
        Export entire database to JSON format.

        Args:
            db: Database session

        Returns:
            Dictionary containing all database tables and metadata
        """
        # Export all tables
        tables = {
            "categories": DatabaseExportService._serialize_categories(db),
            "subscriptions": DatabaseExportService._serialize_subscriptions(db),
            "income_sources": DatabaseExportService._serialize_income_sources(db),
            "income_source_history": DatabaseExportService._serialize_income_source_history(db),
            "transactions": DatabaseExportService._serialize_transactions(db),
            "ignored_transactions": DatabaseExportService._serialize_ignored_transactions(db),
            "name_mappings": DatabaseExportService._serialize_name_mappings(db),
        }

        # Generate metadata
        metadata = DatabaseExportService._generate_metadata(db, tables)

        # Create export object
        export = DatabaseExport(
            version=DatabaseExportService.EXPORT_VERSION,
            exported_at=datetime.now(),
            schema_version=DatabaseExportService.SCHEMA_VERSION,
            tables=tables,
            metadata=metadata
        )

        # Convert to dict and serialize datetime objects
        export_dict = export.model_dump()
        # Pydantic's model_dump with mode='json' serializes datetime to string
        return export.model_dump(mode='json')
