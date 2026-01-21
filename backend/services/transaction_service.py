"""Transaction service for business logic and data operations."""

import logging
from typing import List, Tuple, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.models.transaction import Transaction
from backend.models.ignored_transaction import IgnoredTransaction
from backend.models.subscription import Subscription
from backend.models.category import Category, TransactionCategory
from backend.services.csv_parser import CSVParser
from backend.services.ai_categorizer import AICategorizer
from backend.services.name_mapping_service import NameMappingService
from backend.services.ignore_service import IgnoreService
from backend.services.category_service import CategoryService, SUBSCRIPTIONS_CATEGORY_ID
from backend.schemas.import_preview import (
    PreviewTransactionItem,
    ImportPreviewResponse,
    ImportRequest,
    ImportResult,
    ItemAction
)

logger = logging.getLogger(__name__)


class TransactionService:
    """
    Service for transaction operations including CSV import and CRUD.

    Orchestrates the import flow:
    1. Parse CSV file
    2. Preview transactions (check ignore list and duplicates)
    3. Process user actions (import/ignore/subscription)
    4. Categorize with AI
    5. Store in database
    """

    def __init__(self, db: Session, ai_categorizer: AICategorizer = None):
        """
        Initialize transaction service.

        Args:
            db: SQLAlchemy database session
            ai_categorizer: AI categorizer instance (optional, will create if not provided)
        """
        self.db = db
        self.ai_categorizer = ai_categorizer or AICategorizer()
        self.csv_parser = CSVParser()
        self.name_mapping_service = NameMappingService(db)
        self.ignore_service = IgnoreService(db)
        self.category_service = CategoryService(db)

    def preview_csv_import(self, file_path: str) -> ImportPreviewResponse:
        """
        Parse CSV and generate import preview without saving to database.

        Args:
            file_path: Path to CSV file

        Returns:
            ImportPreviewResponse with parsed items and metadata

        Raises:
            ValueError: If file cannot be parsed
        """
        logger.info(f"Previewing CSV import: {file_path}")

        # Parse CSV file
        source_type, parsed_transactions = self.csv_parser.parse(file_path)

        # Get existing transactions for duplicate detection
        existing_transactions = self._get_existing_transaction_signatures()

        # Build preview items
        preview_items = []
        ignored_count = 0
        duplicate_count = 0

        for idx, transaction_data in enumerate(parsed_transactions):
            # Check if ignored (using fuzzy matching)
            should_ignore, ignore_rule = self.ignore_service.should_ignore(
                transaction_data['description']
            )
            if should_ignore:
                ignored_count += 1
                # Increment usage count for the matched rule
                if ignore_rule:
                    self.ignore_service.increment_usage(ignore_rule.id)

            # Check if duplicate (by date + description + amount)
            signature = self._make_transaction_signature(
                transaction_data['date'],
                transaction_data['description'],
                transaction_data['amount']
            )
            is_duplicate = signature in existing_transactions
            if is_duplicate:
                duplicate_count += 1

            # Find suggested name using fuzzy matching
            suggested_name = self.name_mapping_service.find_suggestion(
                transaction_data['description']
            )

            # Create preview item
            preview_item = PreviewTransactionItem(
                index=idx,
                date=transaction_data['date'],
                description=transaction_data['description'],
                amount=transaction_data['amount'],
                transaction_type=transaction_data.get('transaction_type'),
                original_category=transaction_data.get('original_category'),
                source_type=source_type,
                is_ignored=should_ignore,
                is_duplicate=is_duplicate,
                suggested_name=suggested_name
            )
            preview_items.append(preview_item)

        new_count = len(preview_items) - ignored_count - duplicate_count

        return ImportPreviewResponse(
            source_type=source_type,
            total_items=len(preview_items),
            ignored_count=ignored_count,
            duplicate_count=duplicate_count,
            new_count=new_count,
            items=preview_items
        )

    def import_transactions(self, import_request: ImportRequest) -> ImportResult:
        """
        Import transactions based on user-selected actions.

        Args:
            import_request: Import request with user actions

        Returns:
            ImportResult with import statistics
        """
        logger.info(f"Importing transactions with {len(import_request.actions)} actions")

        imported_count = 0
        ignored_once_count = 0
        ignored_always_count = 0
        subscriptions_created = 0
        errors = []

        # Group actions by type
        actions_by_index = {action.index: action for action in import_request.actions}

        # Separate items: subscriptions don't need AI categorization
        items_to_categorize = []  # Only regular imports need AI categorization
        items_to_import_data = []  # All items to import (with or without AI categorization)
        subscription_items = []  # Items marked as subscription (skip AI)

        # Track descriptions already added to ignore list in this batch
        ignored_in_batch = set()

        for item in import_request.items:
            action = actions_by_index.get(item.index)

            if not action:
                # No action specified, skip
                continue

            # Use edited description if provided, otherwise use original
            final_description = action.edited_description or item.description

            # If user edited the description, create/update name mapping
            if action.edited_description and action.edited_description != item.description:
                try:
                    self.name_mapping_service.create_or_update_mapping(
                        original_description=item.description,
                        mapped_name=action.edited_description
                    )
                    logger.debug(
                        f"Created/updated name mapping: '{item.description}' -> '{action.edited_description}'"
                    )
                except Exception as e:
                    logger.warning(f"Failed to create name mapping: {e}")

            try:
                if action.action == "ignore_once":
                    ignored_once_count += 1
                    logger.debug(f"Ignoring once: {final_description}")

                elif action.action == "ignore_always":
                    # Add to ignore list with fuzzy matching (skip if already added in this batch)
                    if final_description not in ignored_in_batch:
                        self.ignore_service.add_to_ignore_list(final_description)
                        ignored_in_batch.add(final_description)
                        ignored_always_count += 1
                        logger.debug(f"Ignoring always: {final_description}")
                    else:
                        logger.debug(f"Already ignored in batch: {final_description}")

                elif action.action == "subscription":
                    # Subscription items: skip AI categorization, use Assinaturas category
                    subscription_items.append((item, action, final_description))
                    logger.debug(f"Subscription marked (no AI categorization): {final_description}")

                elif action.action == "import":
                    # Regular import: needs AI categorization
                    items_to_categorize.append(final_description)
                    items_to_import_data.append((item, action, final_description))

            except Exception as e:
                error_msg = f"Error processing item {item.index}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Batch categorize regular import items (not subscriptions)
        categories = []
        if items_to_categorize:
            logger.info(f"Categorizing {len(items_to_categorize)} items with AI")
            categories = self.ai_categorizer.categorize_batch(items_to_categorize)

        # Process regular imports with AI categorization
        for (item, action, final_description), category_name in zip(items_to_import_data, categories):
            try:
                # Regular import: use AI category
                category = self.category_service.find_or_create_category(category_name)
                category_id = category.id

                # Create transaction
                transaction = Transaction(
                    date=item.date,
                    description=final_description,
                    amount=item.amount,
                    currency="BRL",
                    transaction_type=item.transaction_type,
                    original_category=item.original_category,
                    category_id=category_id,
                    source_type=item.source_type,
                    source_file=import_request.source_file,
                    subscription_id=None  # Regular imports are not linked to subscriptions
                )

                self.db.add(transaction)
                imported_count += 1

            except Exception as e:
                error_msg = f"Error importing item {item.index} ({final_description}): {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Process subscription items (no AI categorization, always Assinaturas)
        for item, action, final_description in subscription_items:
            try:
                # Create subscription
                subscription = self._create_or_get_subscription(
                    action.subscription_name or final_description,
                    final_description,
                    item.amount
                )
                subscriptions_created += 1 if subscription else 0

                # Create transaction with Assinaturas category
                transaction = Transaction(
                    date=item.date,
                    description=final_description,
                    amount=item.amount,
                    currency="BRL",
                    transaction_type=item.transaction_type,
                    original_category=item.original_category,
                    category_id=SUBSCRIPTIONS_CATEGORY_ID,  # Always Assinaturas
                    source_type=item.source_type,
                    source_file=import_request.source_file,
                    subscription_id=subscription.id if subscription else None
                )

                self.db.add(transaction)
                imported_count += 1

                # Update subscription current_value
                if subscription:
                    subscription.current_value = item.amount
                    subscription.updated_at = datetime.utcnow()

            except Exception as e:
                error_msg = f"Error importing subscription item {item.index} ({final_description}): {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Commit all changes
        try:
            self.db.commit()
            logger.info(f"Import completed: {imported_count} imported, "
                       f"{subscriptions_created} subscriptions created")
        except Exception as e:
            self.db.rollback()
            error_msg = f"Error committing to database: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

        return ImportResult(
            total_processed=len(import_request.actions),
            imported_count=imported_count,
            ignored_once_count=ignored_once_count,
            ignored_always_count=ignored_always_count,
            subscriptions_created=subscriptions_created,
            errors=errors
        )

    def get_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Transaction], int]:
        """
        Get transactions with optional filters.

        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            category: Filter by category
            search: Search in description
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (transactions list, total count)
        """
        query = self.db.query(Transaction)

        # Apply filters
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        if category:
            # Join with Category table to filter by name
            query = query.join(Category).filter(Category.name == category)
        if search:
            query = query.filter(Transaction.description.ilike(f"%{search}%"))

        # Get total count
        total = query.count()

        # Apply pagination and order
        transactions = query.order_by(Transaction.date.desc()).limit(limit).offset(offset).all()

        return transactions, total

    def update_transaction_category(self, transaction_id: int, category_name: str) -> Optional[Transaction]:
        """
        Update a transaction's category.

        Special rules:
        - Subscription transactions (those with subscription_id) must keep the Assinaturas category
        - The Assinaturas category can only be assigned through subscription import

        Args:
            transaction_id: Transaction ID
            category_name: New category name

        Returns:
            Updated transaction or None if not found

        Raises:
            ValueError: If attempting to violate subscription category rules
        """
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            # Find or create category using fuzzy matching
            category = self.category_service.find_or_create_category(category_name)

            # Prevent changing category of subscription transactions
            if transaction.subscription_id and category.id != SUBSCRIPTIONS_CATEGORY_ID:
                raise ValueError(
                    "Cannot change category of a subscription transaction. "
                    "Subscription transactions must use the 'Assinaturas' category."
                )

            # Prevent manually assigning Assinaturas category to non-subscription transactions
            if category.id == SUBSCRIPTIONS_CATEGORY_ID and not transaction.subscription_id:
                raise ValueError(
                    "The 'Assinaturas' category can only be assigned to subscription transactions. "
                    "To categorize this as a subscription, link it to a subscription first."
                )

            transaction.category_id = category.id
            self.db.commit()
            logger.info(f"Updated transaction {transaction_id} category to {category_name}")
        return transaction

    def delete_transaction(self, transaction_id: int) -> bool:
        """
        Delete a transaction.

        Args:
            transaction_id: Transaction ID

        Returns:
            True if deleted, False if not found
        """
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            self.db.delete(transaction)
            self.db.commit()
            logger.info(f"Deleted transaction {transaction_id}")
            return True
        return False

    # Helper methods

    def _get_ignored_descriptions(self) -> set:
        """Get set of ignored transaction descriptions."""
        ignored = self.db.query(IgnoredTransaction.description).all()
        return {desc[0] for desc in ignored}

    def _get_existing_transaction_signatures(self) -> set:
        """Get set of existing transaction signatures (date+description+amount)."""
        transactions = self.db.query(Transaction.date, Transaction.description, Transaction.amount).all()
        return {self._make_transaction_signature(t[0], t[1], t[2]) for t in transactions}

    def _make_transaction_signature(self, date: date, description: str, amount: float) -> str:
        """Create a signature for duplicate detection."""
        return f"{date.isoformat()}|{description}|{amount:.2f}"

    def _add_to_ignore_list(self, description: str) -> None:
        """Add description to ignore list if not already present."""
        try:
            existing = self.db.query(IgnoredTransaction).filter(
                IgnoredTransaction.description == description
            ).first()

            if not existing:
                ignored = IgnoredTransaction(description=description)
                self.db.add(ignored)
                # Flush to catch constraint errors early
                self.db.flush()
                logger.info(f"Added to ignore list: {description}")
        except Exception as e:
            # If it's a duplicate, that's fine - item is already ignored
            logger.debug(f"Could not add to ignore list (may already exist): {description}")

    def _create_or_get_subscription(
        self,
        name: str,
        description: str,
        amount: float
    ) -> Optional[Subscription]:
        """Create a new subscription or get existing one by description pattern."""
        # Check if subscription already exists with this description pattern
        existing = self.db.query(Subscription).filter(
            Subscription.pattern == description
        ).first()

        if existing:
            logger.info(f"Found existing subscription: {existing.name}")
            return existing

        # Create new subscription
        try:
            subscription = Subscription(
                name=name,
                description=f"Auto-created from import: {description}",
                current_value=amount,
                pattern=description,  # Use exact description as pattern for matching
                is_active=True
            )
            self.db.add(subscription)
            self.db.flush()  # Get the ID without committing
            logger.info(f"Created subscription: {name}")
            return subscription
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return None
