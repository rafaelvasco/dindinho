"""Service for managing ignored transactions with fuzzy matching support."""

import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from rapidfuzz import fuzz, process

from backend.models.ignored_transaction import IgnoredTransaction

logger = logging.getLogger(__name__)


class IgnoreService:
    """
    Service for managing ignored transactions with fuzzy matching.

    Provides functionality to:
    - Check if description should be ignored (exact or fuzzy match)
    - Add descriptions to ignore list
    - Manage ignore rules with thresholds
    """

    DEFAULT_THRESHOLD = 70.0  # 70% similarity threshold

    def __init__(self, db: Session):
        """
        Initialize ignore service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def should_ignore(self, description: str) -> Tuple[bool, Optional[IgnoredTransaction]]:
        """
        Check if a description should be ignored using exact or fuzzy matching.

        Args:
            description: Transaction description to check

        Returns:
            Tuple of (should_ignore, matched_rule)
            - should_ignore: True if description matches an ignore rule
            - matched_rule: The IgnoredTransaction object that matched, or None
        """
        # Get all ignore rules
        ignore_rules = self.db.query(IgnoredTransaction).all()

        if not ignore_rules:
            return (False, None)

        # First, try exact matches (faster)
        for rule in ignore_rules:
            if description == rule.description:
                logger.debug(f"Exact ignore match: '{description}' matches rule '{rule.description}'")
                return (True, rule)

        # Then, try fuzzy matches for rules that have a threshold
        fuzzy_rules = [r for r in ignore_rules if r.fuzzy_threshold is not None]

        if not fuzzy_rules:
            return (False, None)

        # Find best fuzzy match
        for rule in fuzzy_rules:
            similarity = fuzz.ratio(description, rule.description)

            if similarity >= rule.fuzzy_threshold:
                logger.info(
                    f"Fuzzy ignore match: '{description}' matches rule '{rule.description}' "
                    f"(score: {similarity:.1f}, threshold: {rule.fuzzy_threshold})"
                )
                return (True, rule)

        return (False, None)

    def get_ignored_descriptions_set(self) -> set:
        """
        Get set of ignored expense descriptions (for backward compatibility).

        Returns:
            Set of ignored description strings
        """
        ignored = self.db.query(IgnoredTransaction.description).all()
        return {desc[0] for desc in ignored}

    def add_to_ignore_list(
        self,
        description: str,
        fuzzy_threshold: Optional[float] = None
    ) -> IgnoredTransaction:
        """
        Add description to ignore list.

        Args:
            description: Description to ignore
            fuzzy_threshold: Fuzzy matching threshold (None for exact matching only)

        Returns:
            The created or existing IgnoredTransaction object
        """
        if fuzzy_threshold is None:
            fuzzy_threshold = self.DEFAULT_THRESHOLD

        # Check if already exists
        existing = self.db.query(IgnoredTransaction).filter(
            IgnoredTransaction.description == description
        ).first()

        if existing:
            # Update threshold if different
            if existing.fuzzy_threshold != fuzzy_threshold:
                existing.fuzzy_threshold = fuzzy_threshold
                self.db.commit()
                logger.info(f"Updated ignore rule threshold: '{description}' -> {fuzzy_threshold}")
            return existing

        # Create new ignore rule
        ignored = IgnoredTransaction(
            description=description,
            fuzzy_threshold=fuzzy_threshold,
            usage_count=0
        )

        self.db.add(ignored)
        self.db.commit()
        self.db.refresh(ignored)

        logger.info(f"Added to ignore list: '{description}' (threshold: {fuzzy_threshold})")

        return ignored

    def increment_usage(self, rule_id: int) -> None:
        """
        Increment the usage count for an ignore rule.

        Args:
            rule_id: ID of the rule to increment
        """
        rule = self.db.query(IgnoredTransaction).filter(IgnoredTransaction.id == rule_id).first()

        if rule:
            rule.usage_count += 1
            self.db.commit()
            logger.debug(f"Incremented ignore rule usage: {rule_id} -> {rule.usage_count}")

    def get_all_rules(self) -> List[IgnoredTransaction]:
        """
        Get all ignore rules.

        Returns:
            List of all IgnoredTransaction objects
        """
        return self.db.query(IgnoredTransaction).order_by(IgnoredTransaction.usage_count.desc()).all()

    def delete_rule(self, rule_id: int) -> bool:
        """
        Delete an ignore rule.

        Args:
            rule_id: ID of the rule to delete

        Returns:
            True if deleted, False if not found
        """
        rule = self.db.query(IgnoredTransaction).filter(IgnoredTransaction.id == rule_id).first()

        if rule:
            self.db.delete(rule)
            self.db.commit()
            logger.info(f"Deleted ignore rule {rule_id}: '{rule.description}'")
            return True

        return False
