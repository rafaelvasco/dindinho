"""Service for importing database from JSON format."""

from datetime import datetime, date
from typing import Dict, Any, List, Set, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.models.transaction import Transaction, TransactionType
from backend.models.category import Category
from backend.models.subscription import Subscription
from backend.models.income_source import IncomeSource, IncomeSourceHistory
from backend.models.ignored_transaction import IgnoredTransaction
from backend.models.name_mapping import NameMapping
from backend.schemas.database_export import ImportPreview, ConflictSummary, ImportResult


class DatabaseImportService:
    """Service to handle database import operations."""

    SUPPORTED_VERSIONS = ["1.0"]
    SUPPORTED_SCHEMA_VERSIONS = ["1"]

    @staticmethod
    def validate_json(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate JSON structure and compatibility.

        Args:
            data: Import data dictionary

        Returns:
            Tuple of (is_valid, errors_list)
        """
        errors = []

        # Check required fields
        required_fields = ["version", "exported_at", "schema_version", "tables", "metadata"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        if errors:
            return False, errors

        # Check version compatibility
        if data["version"] not in DatabaseImportService.SUPPORTED_VERSIONS:
            errors.append(
                f"Unsupported export version: {data['version']}. "
                f"Supported versions: {', '.join(DatabaseImportService.SUPPORTED_VERSIONS)}"
            )

        if data["schema_version"] not in DatabaseImportService.SUPPORTED_SCHEMA_VERSIONS:
            errors.append(
                f"Unsupported schema version: {data['schema_version']}. "
                f"Supported versions: {', '.join(DatabaseImportService.SUPPORTED_SCHEMA_VERSIONS)}"
            )

        # Check tables structure
        if not isinstance(data.get("tables"), dict):
            errors.append("'tables' field must be a dictionary")
        else:
            required_tables = [
                "categories", "subscriptions", "income_sources",
                "income_source_history", "transactions",
                "ignored_transactions", "name_mappings"
            ]
            for table in required_tables:
                if table not in data["tables"]:
                    errors.append(f"Missing required table: {table}")
                elif not isinstance(data["tables"][table], list):
                    errors.append(f"Table '{table}' must be a list")

        return len(errors) == 0, errors

    @staticmethod
    def _detect_duplicate_categories(db: Session, items: List[Dict]) -> Set[int]:
        """
        Detect duplicate categories by name (case-insensitive).

        Returns:
            Set of indices of duplicate items
        """
        duplicates = set()
        existing_names = {cat.name.lower() for cat in db.query(Category).all()}

        for idx, item in enumerate(items):
            if item.get("name", "").lower() in existing_names:
                duplicates.add(idx)

        return duplicates

    @staticmethod
    def _detect_duplicate_subscriptions(db: Session, items: List[Dict]) -> Set[int]:
        """
        Detect duplicate subscriptions by name.

        Returns:
            Set of indices of duplicate items
        """
        duplicates = set()
        existing_names = {sub.name for sub in db.query(Subscription).all()}

        for idx, item in enumerate(items):
            if item.get("name") in existing_names:
                duplicates.add(idx)

        return duplicates

    @staticmethod
    def _detect_duplicate_income_sources(db: Session, items: List[Dict]) -> Set[int]:
        """
        Detect duplicate income sources by name or CNPJ.

        Returns:
            Set of indices of duplicate items
        """
        duplicates = set()
        existing_names = {source.name for source in db.query(IncomeSource).all()}
        existing_cnpjs = {source.cnpj for source in db.query(IncomeSource).all() if source.cnpj}

        for idx, item in enumerate(items):
            name = item.get("name")
            cnpj = item.get("cnpj")

            if name in existing_names or (cnpj and cnpj in existing_cnpjs):
                duplicates.add(idx)

        return duplicates

    @staticmethod
    def _detect_duplicate_transactions(db: Session, items: List[Dict]) -> Set[int]:
        """
        Detect duplicate transactions by date + description + amount.

        Returns:
            Set of indices of duplicate items
        """
        duplicates = set()

        # Build set of existing transaction signatures
        existing_sigs = set()
        for txn in db.query(Transaction).all():
            sig = (txn.date.isoformat(), txn.description, txn.amount)
            existing_sigs.add(sig)

        for idx, item in enumerate(items):
            sig = (item.get("date"), item.get("description"), item.get("amount"))
            if sig in existing_sigs:
                duplicates.add(idx)

        return duplicates

    @staticmethod
    def _detect_duplicate_ignored_transactions(db: Session, items: List[Dict]) -> Set[int]:
        """
        Detect duplicate ignored transactions by description pattern.

        Returns:
            Set of indices of duplicate items
        """
        duplicates = set()
        existing_patterns = {ign.description for ign in db.query(IgnoredTransaction).all()}

        for idx, item in enumerate(items):
            if item.get("description") in existing_patterns:
                duplicates.add(idx)

        return duplicates

    @staticmethod
    def _detect_duplicate_name_mappings(db: Session, items: List[Dict]) -> Set[int]:
        """
        Detect duplicate name mappings by pattern.

        Returns:
            Set of indices of duplicate items
        """
        duplicates = set()
        existing_patterns = {mapping.pattern for mapping in db.query(NameMapping).all()}

        for idx, item in enumerate(items):
            if item.get("pattern") in existing_patterns:
                duplicates.add(idx)

        return duplicates

    @staticmethod
    def preview_import(db: Session, data: Dict[str, Any]) -> ImportPreview:
        """
        Preview what will happen during import without making changes.

        Args:
            db: Database session
            data: Import data dictionary

        Returns:
            ImportPreview with conflict analysis
        """
        # Validate JSON
        is_valid, errors = DatabaseImportService.validate_json(data)
        if not is_valid:
            return ImportPreview(
                valid=False,
                schema_compatible=False,
                conflicts={},
                total_new_records=0,
                total_skipped_records=0,
                errors=errors
            )

        tables = data["tables"]
        conflicts = {}
        total_new = 0
        total_skipped = 0

        # Analyze each table
        table_analyzers = {
            "categories": DatabaseImportService._detect_duplicate_categories,
            "subscriptions": DatabaseImportService._detect_duplicate_subscriptions,
            "income_sources": DatabaseImportService._detect_duplicate_income_sources,
            "transactions": DatabaseImportService._detect_duplicate_transactions,
            "ignored_transactions": DatabaseImportService._detect_duplicate_ignored_transactions,
            "name_mappings": DatabaseImportService._detect_duplicate_name_mappings,
        }

        for table_name, analyzer in table_analyzers.items():
            items = tables.get(table_name, [])
            duplicates = analyzer(db, items)

            total = len(items)
            skipped = len(duplicates)
            new = total - skipped

            conflicts[table_name] = ConflictSummary(
                total=total,
                new=new,
                duplicates=skipped
            )

            total_new += new
            total_skipped += skipped

        # Income source history - count all as new (will be filtered by parent)
        history_items = tables.get("income_source_history", [])
        conflicts["income_source_history"] = ConflictSummary(
            total=len(history_items),
            new=len(history_items),
            duplicates=0
        )

        return ImportPreview(
            valid=True,
            schema_compatible=True,
            conflicts=conflicts,
            total_new_records=total_new,
            total_skipped_records=total_skipped,
            errors=[]
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[date]:
        """Parse ISO date string."""
        if not date_str:
            return None
        return datetime.fromisoformat(date_str).date()

    @staticmethod
    def _parse_datetime(datetime_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string."""
        if not datetime_str:
            return None
        return datetime.fromisoformat(datetime_str)

    @staticmethod
    def execute_import(db: Session, data: Dict[str, Any]) -> ImportResult:
        """
        Execute database import with "skip duplicates" strategy.

        Args:
            db: Database session
            data: Import data dictionary

        Returns:
            ImportResult with statistics
        """
        # Validate first
        is_valid, errors = DatabaseImportService.validate_json(data)
        if not is_valid:
            return ImportResult(
                success=False,
                imported={},
                skipped={},
                errors=errors
            )

        imported_counts = {}
        skipped_counts = {}
        tables = data["tables"]

        try:
            # Import in order (respecting foreign key dependencies)

            # 1. Categories
            categories_data = tables.get("categories", [])
            duplicates = DatabaseImportService._detect_duplicate_categories(db, categories_data)
            category_id_map = {}  # old_id -> new_id

            for idx, item in enumerate(categories_data):
                if idx in duplicates:
                    # Map to existing category
                    existing = db.query(Category).filter(
                        Category.name == item["name"]
                    ).first()
                    if existing:
                        category_id_map[item["id"]] = existing.id
                    continue

                old_id = item.pop("id")
                category = Category(**{
                    k: v for k, v in item.items()
                    if k in ["name", "created_at", "updated_at"]
                })
                if item.get("created_at"):
                    category.created_at = DatabaseImportService._parse_datetime(item["created_at"])
                if item.get("updated_at"):
                    category.updated_at = DatabaseImportService._parse_datetime(item["updated_at"])

                db.add(category)
                db.flush()
                category_id_map[old_id] = category.id

            imported_counts["categories"] = len(categories_data) - len(duplicates)
            skipped_counts["categories"] = len(duplicates)

            # 2. Subscriptions
            subscriptions_data = tables.get("subscriptions", [])
            duplicates = DatabaseImportService._detect_duplicate_subscriptions(db, subscriptions_data)
            subscription_id_map = {}  # old_id -> new_id

            for idx, item in enumerate(subscriptions_data):
                if idx in duplicates:
                    # Map to existing subscription
                    existing = db.query(Subscription).filter(
                        Subscription.name == item["name"]
                    ).first()
                    if existing:
                        subscription_id_map[item["id"]] = existing.id
                    continue

                old_id = item.pop("id")
                subscription = Subscription(
                    name=item["name"],
                    description=item.get("description"),
                    is_active=item.get("is_active", True),
                    current_value=item["current_value"],
                    currency=item.get("currency", "BRL"),
                    pattern=item.get("pattern")
                )
                if item.get("created_at"):
                    subscription.created_at = DatabaseImportService._parse_datetime(item["created_at"])
                if item.get("updated_at"):
                    subscription.updated_at = DatabaseImportService._parse_datetime(item["updated_at"])

                db.add(subscription)
                db.flush()
                subscription_id_map[old_id] = subscription.id

            imported_counts["subscriptions"] = len(subscriptions_data) - len(duplicates)
            skipped_counts["subscriptions"] = len(duplicates)

            # 3. Income Sources
            income_sources_data = tables.get("income_sources", [])
            duplicates = DatabaseImportService._detect_duplicate_income_sources(db, income_sources_data)
            income_source_id_map = {}  # old_id -> new_id

            for idx, item in enumerate(income_sources_data):
                if idx in duplicates:
                    # Map to existing income source
                    existing = db.query(IncomeSource).filter(
                        (IncomeSource.name == item["name"]) |
                        (IncomeSource.cnpj == item.get("cnpj"))
                    ).first()
                    if existing:
                        income_source_id_map[item["id"]] = existing.id
                    continue

                old_id = item.pop("id")
                income_source = IncomeSource(
                    name=item["name"],
                    cnpj=item.get("cnpj"),
                    description=item.get("description"),
                    is_active=item.get("is_active", True),
                    current_expected_amount=item["current_expected_amount"],
                    currency=item.get("currency", "BRL")
                )
                if item.get("created_at"):
                    income_source.created_at = DatabaseImportService._parse_datetime(item["created_at"])
                if item.get("updated_at"):
                    income_source.updated_at = DatabaseImportService._parse_datetime(item["updated_at"])

                db.add(income_source)
                db.flush()
                income_source_id_map[old_id] = income_source.id

            imported_counts["income_sources"] = len(income_sources_data) - len(duplicates)
            skipped_counts["income_sources"] = len(duplicates)

            # 4. Income Source History (only for new income sources)
            history_data = tables.get("income_source_history", [])
            imported_history = 0

            for item in history_data:
                old_income_source_id = item["income_source_id"]

                # Only import if we imported the parent income source
                if old_income_source_id in income_source_id_map:
                    new_income_source_id = income_source_id_map[old_income_source_id]

                    history = IncomeSourceHistory(
                        income_source_id=new_income_source_id,
                        expected_amount=item["expected_amount"],
                        effective_date=DatabaseImportService._parse_datetime(item["effective_date"]),
                        note=item.get("note")
                    )
                    db.add(history)
                    imported_history += 1

            imported_counts["income_source_history"] = imported_history
            skipped_counts["income_source_history"] = len(history_data) - imported_history

            # 5. Transactions
            transactions_data = tables.get("transactions", [])
            duplicates = DatabaseImportService._detect_duplicate_transactions(db, transactions_data)

            for idx, item in enumerate(transactions_data):
                if idx in duplicates:
                    continue

                # Remap foreign keys
                new_category_id = category_id_map.get(item["category_id"])
                if not new_category_id:
                    # Skip if category doesn't exist
                    continue

                # Remap optional foreign keys
                new_subscription_id = None
                if item.get("subscription_id"):
                    new_subscription_id = subscription_id_map.get(item["subscription_id"])

                new_income_source_id = None
                if item.get("income_source_id"):
                    new_income_source_id = income_source_id_map.get(item["income_source_id"])

                transaction = Transaction(
                    date=DatabaseImportService._parse_date(item["date"]),
                    description=item["description"],
                    amount=item["amount"],
                    currency=item.get("currency", "BRL"),
                    original_category=item.get("original_category"),
                    category_id=new_category_id,
                    transaction_type=TransactionType(item["transaction_type"]),
                    source_file=item.get("source_file"),
                    source_type=item["source_type"],
                    raw_data=item.get("raw_data"),
                    subscription_id=new_subscription_id,
                    income_source_id=new_income_source_id
                )
                if item.get("created_at"):
                    transaction.created_at = DatabaseImportService._parse_datetime(item["created_at"])
                if item.get("updated_at"):
                    transaction.updated_at = DatabaseImportService._parse_datetime(item["updated_at"])

                db.add(transaction)

            imported_counts["transactions"] = len(transactions_data) - len(duplicates)
            skipped_counts["transactions"] = len(duplicates)

            # 6. Ignored Transactions
            ignored_data = tables.get("ignored_transactions", [])
            duplicates = DatabaseImportService._detect_duplicate_ignored_transactions(db, ignored_data)

            for idx, item in enumerate(ignored_data):
                if idx in duplicates:
                    continue

                ignored = IgnoredTransaction(
                    description=item["description"],
                    fuzzy_threshold=item.get("fuzzy_threshold"),
                    usage_count=item.get("usage_count", 0)
                )
                if item.get("created_at"):
                    ignored.created_at = DatabaseImportService._parse_datetime(item["created_at"])

                db.add(ignored)

            imported_counts["ignored_transactions"] = len(ignored_data) - len(duplicates)
            skipped_counts["ignored_transactions"] = len(duplicates)

            # 7. Name Mappings
            mappings_data = tables.get("name_mappings", [])
            duplicates = DatabaseImportService._detect_duplicate_name_mappings(db, mappings_data)

            for idx, item in enumerate(mappings_data):
                if idx in duplicates:
                    continue

                mapping = NameMapping(
                    pattern=item["pattern"],
                    mapped_name=item["mapped_name"],
                    fuzzy_threshold=item.get("fuzzy_threshold", 70.0),
                    usage_count=item.get("usage_count", 0)
                )
                if item.get("created_at"):
                    mapping.created_at = DatabaseImportService._parse_datetime(item["created_at"])
                if item.get("updated_at"):
                    mapping.updated_at = DatabaseImportService._parse_datetime(item["updated_at"])

                db.add(mapping)

            imported_counts["name_mappings"] = len(mappings_data) - len(duplicates)
            skipped_counts["name_mappings"] = len(duplicates)

            # Commit all changes
            db.commit()

            return ImportResult(
                success=True,
                imported=imported_counts,
                skipped=skipped_counts,
                errors=[]
            )

        except Exception as e:
            db.rollback()
            return ImportResult(
                success=False,
                imported={},
                skipped={},
                errors=[f"Import failed: {str(e)}"]
            )
