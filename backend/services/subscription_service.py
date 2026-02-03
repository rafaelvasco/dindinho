"""Subscription service for managing recurring expenses."""

import logging
from typing import List, Optional, Tuple
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.subscription import Subscription
from backend.models.transaction import Transaction

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Service for subscription operations.

    Handles:
    - CRUD operations for subscriptions
    - Linking expenses to subscriptions
    - Updating current_value from most recent expense
    - Auto-linking future imports via exact description match
    """

    def __init__(self, db: Session):
        """
        Initialize subscription service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_subscription(
        self,
        name: str,
        pattern: Optional[str] = None,
        description: Optional[str] = None,
        initial_value: float = 0.0
    ) -> Subscription:
        """
        Create a new subscription.

        Args:
            name: Subscription name (must be unique)
            pattern: Exact description pattern for matching expenses
            description: Optional description
            initial_value: Initial value (default: 0.0)

        Returns:
            Created subscription

        Raises:
            ValueError: If subscription with this name already exists
        """
        # Check if subscription with this name exists
        existing = self.db.query(Subscription).filter(
            Subscription.name == name
        ).first()

        if existing:
            raise ValueError(f"Subscription with name '{name}' already exists")

        subscription = Subscription(
            name=name,
            description=description,
            pattern=pattern,
            current_value=initial_value,
            is_active=True
        )

        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)

        logger.info(f"Created subscription: {name}")
        return subscription

    def get_subscription(self, subscription_id: int) -> Optional[Subscription]:
        """
        Get subscription by ID.

        Args:
            subscription_id: Subscription ID

        Returns:
            Subscription or None if not found
        """
        return self.db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()

    def get_all_subscriptions(
        self,
        active_only: bool = False
    ) -> List[Subscription]:
        """
        Get all subscriptions.

        Args:
            active_only: If True, only return active subscriptions

        Returns:
            List of subscriptions
        """
        query = self.db.query(Subscription)

        if active_only:
            query = query.filter(Subscription.is_active == True)

        return query.order_by(Subscription.name).all()

    def update_subscription(
        self,
        subscription_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        pattern: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Subscription]:
        """
        Update subscription details.

        Args:
            subscription_id: Subscription ID
            name: New name (optional)
            description: New description (optional)
            pattern: New pattern (optional)
            is_active: New active status (optional)

        Returns:
            Updated subscription or None if not found
        """
        subscription = self.get_subscription(subscription_id)

        if not subscription:
            return None

        if name is not None:
            subscription.name = name
        if description is not None:
            subscription.description = description
        if pattern is not None:
            subscription.pattern = pattern
        if is_active is not None:
            subscription.is_active = is_active

        self.db.commit()
        self.db.refresh(subscription)

        logger.info(f"Updated subscription {subscription_id}")
        return subscription

    def delete_subscription(self, subscription_id: int) -> bool:
        """
        Delete a subscription.

        Note: This will unlink all associated expenses but not delete them.

        Args:
            subscription_id: Subscription ID

        Returns:
            True if deleted, False if not found
        """
        subscription = self.get_subscription(subscription_id)

        if not subscription:
            return False

        # Unlink all transactions
        for transaction in subscription.transactions:
            transaction.subscription_id = None

        self.db.delete(subscription)
        self.db.commit()

        logger.info(f"Deleted subscription {subscription_id}")
        return True

    def link_transaction_to_subscription(
        self,
        transaction_id: int,
        subscription_id: int
    ) -> Tuple[Transaction, Subscription]:
        """
        Link a transaction to a subscription and update subscription's current_value.

        Args:
            transaction_id: Transaction ID
            subscription_id: Subscription ID

        Returns:
            Tuple of (transaction, subscription) or None if either not found

        Raises:
            ValueError: If transaction or subscription not found
        """
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        subscription = self.get_subscription(subscription_id)

        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        # Link transaction to subscription
        transaction.subscription_id = subscription_id

        # Update subscription's current_value to this transaction's amount
        # (assuming this is the most recent transaction)
        subscription.current_value = transaction.amount

        self.db.commit()
        self.db.refresh(transaction)
        self.db.refresh(subscription)

        logger.info(f"Linked transaction {transaction_id} to subscription {subscription_id}")
        return transaction, subscription

    def unlink_transaction_from_subscription(self, transaction_id: int) -> Optional[Transaction]:
        """
        Unlink a transaction from its subscription.

        Args:
            transaction_id: Transaction ID

        Returns:
            Updated transaction or None if not found
        """
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()

        if not transaction:
            return None

        old_subscription_id = transaction.subscription_id
        transaction.subscription_id = None

        self.db.commit()
        self.db.refresh(transaction)

        # Update subscription's current_value to the most recent remaining transaction
        if old_subscription_id:
            self._update_subscription_current_value(old_subscription_id)

        logger.info(f"Unlinked transaction {transaction_id} from subscription")
        return transaction

    def get_subscription_history(
        self,
        subscription_id: int
    ) -> Optional[List[Tuple[date, float]]]:
        """
        Get historical values for a subscription.

        Args:
            subscription_id: Subscription ID

        Returns:
            List of (date, amount) tuples sorted by date, or None if not found
        """
        subscription = self.get_subscription(subscription_id)

        if not subscription:
            return None

        return subscription.historical_values

    def find_subscription_by_pattern(self, description: str) -> Optional[Subscription]:
        """
        Find subscription by exact description pattern match.

        This is used during CSV import to auto-link transactions to existing subscriptions.

        Args:
            description: Transaction description

        Returns:
            Matching subscription or None
        """
        return self.db.query(Subscription).filter(
            Subscription.pattern == description,
            Subscription.is_active == True
        ).first()

    def _update_subscription_current_value(self, subscription_id: int) -> None:
        """
        Update subscription's current_value to the most recent expense amount.

        Args:
            subscription_id: Subscription ID
        """
        subscription = self.get_subscription(subscription_id)

        if not subscription:
            return

        # Get most recent expense for this subscription
        most_recent = self.db.query(Transaction).filter(
            Transaction.subscription_id == subscription_id
        ).order_by(desc(Transaction.date)).first()

        if most_recent:
            subscription.current_value = most_recent.amount
            self.db.commit()
            logger.info(f"Updated subscription {subscription_id} current_value to {most_recent.amount}")
        else:
            # No expenses linked, set to 0
            subscription.current_value = 0.0
            self.db.commit()
            logger.info(f"Reset subscription {subscription_id} current_value to 0.0 (no expenses)")
