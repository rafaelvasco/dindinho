"""Service for managing fuzzy name mappings for expense descriptions."""

import logging
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from rapidfuzz import fuzz, process

from backend.models.name_mapping import NameMapping

logger = logging.getLogger(__name__)


class NameMappingService:
    """
    Service for fuzzy matching and managing name mappings.

    Provides functionality to:
    - Find suggested names based on fuzzy matching
    - Create new mappings
    - Update existing mappings
    - Manage mapping lifecycle
    """

    DEFAULT_THRESHOLD = 70.0  # 70% similarity threshold

    def __init__(self, db: Session):
        """
        Initialize name mapping service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def find_suggestion(self, description: str, threshold: float = None) -> Optional[str]:
        """
        Find a suggested mapped name for a description using fuzzy matching.

        Args:
            description: Original expense description
            threshold: Minimum similarity score (0-100). Defaults to 70.

        Returns:
            Suggested mapped name if a match is found, None otherwise
        """
        if threshold is None:
            threshold = self.DEFAULT_THRESHOLD

        # Get all existing mappings
        mappings = self.db.query(NameMapping).all()

        if not mappings:
            return None

        # Build list of patterns with their mapped names
        patterns = [(m.pattern, m) for m in mappings]

        # Find best match using fuzzy matching
        best_match = process.extractOne(
            description,
            [p[0] for p in patterns],
            scorer=fuzz.ratio,
            score_cutoff=threshold
        )

        if best_match:
            matched_pattern = best_match[0]
            score = best_match[1]

            # Find the mapping for this pattern
            mapping = next(m for p, m in patterns if p == matched_pattern)

            logger.info(
                f"Found suggestion for '{description}': '{mapping.mapped_name}' "
                f"(matched pattern: '{matched_pattern}', score: {score:.1f})"
            )

            return mapping.mapped_name

        return None

    def find_suggestion_with_details(
        self,
        description: str,
        threshold: float = None
    ) -> Optional[Tuple[str, NameMapping, float]]:
        """
        Find a suggested mapped name with detailed match information.

        Args:
            description: Original expense description
            threshold: Minimum similarity score (0-100). Defaults to 70.

        Returns:
            Tuple of (suggested_name, mapping_obj, score) if match found, None otherwise
        """
        if threshold is None:
            threshold = self.DEFAULT_THRESHOLD

        # Get all existing mappings
        mappings = self.db.query(NameMapping).all()

        if not mappings:
            return None

        # Build list of patterns with their mapped names
        patterns = [(m.pattern, m) for m in mappings]

        # Find best match using fuzzy matching
        best_match = process.extractOne(
            description,
            [p[0] for p in patterns],
            scorer=fuzz.ratio,
            score_cutoff=threshold
        )

        if best_match:
            matched_pattern = best_match[0]
            score = best_match[1]

            # Find the mapping for this pattern
            mapping = next(m for p, m in patterns if p == matched_pattern)

            logger.debug(
                f"Found suggestion for '{description}': '{mapping.mapped_name}' "
                f"(pattern: '{matched_pattern}', score: {score:.1f})"
            )

            return (mapping.mapped_name, mapping, score)

        return None

    def create_or_update_mapping(
        self,
        original_description: str,
        mapped_name: str,
        threshold: float = None
    ) -> NameMapping:
        """
        Create a new mapping or update existing one if similar pattern exists.

        Args:
            original_description: Original expense description pattern
            mapped_name: The mapped/renamed value
            threshold: Fuzzy matching threshold for finding existing mappings

        Returns:
            The created or updated NameMapping object
        """
        if threshold is None:
            threshold = self.DEFAULT_THRESHOLD

        # Check if there's an existing mapping for a similar pattern
        match_result = self.find_suggestion_with_details(original_description, threshold)

        if match_result:
            suggested_name, existing_mapping, score = match_result

            # Update existing mapping
            existing_mapping.pattern = original_description
            existing_mapping.mapped_name = mapped_name
            existing_mapping.usage_count = 0  # Reset usage count

            self.db.commit()
            self.db.refresh(existing_mapping)

            logger.info(
                f"Updated existing mapping (ID: {existing_mapping.id}): "
                f"'{original_description}' -> '{mapped_name}' "
                f"(replaced '{suggested_name}', score: {score:.1f})"
            )

            return existing_mapping

        # Create new mapping
        new_mapping = NameMapping(
            pattern=original_description,
            mapped_name=mapped_name,
            fuzzy_threshold=threshold,
            usage_count=0
        )

        self.db.add(new_mapping)
        self.db.commit()
        self.db.refresh(new_mapping)

        logger.info(
            f"Created new mapping (ID: {new_mapping.id}): "
            f"'{original_description}' -> '{mapped_name}'"
        )

        return new_mapping

    def increment_usage(self, mapping_id: int) -> None:
        """
        Increment the usage count for a mapping.

        Args:
            mapping_id: ID of the mapping to increment
        """
        mapping = self.db.query(NameMapping).filter(NameMapping.id == mapping_id).first()

        if mapping:
            mapping.usage_count += 1
            self.db.commit()
            logger.debug(f"Incremented usage count for mapping {mapping_id}: {mapping.usage_count}")

    def get_all_mappings(self) -> List[NameMapping]:
        """
        Get all name mappings.

        Returns:
            List of all NameMapping objects
        """
        return self.db.query(NameMapping).order_by(NameMapping.usage_count.desc()).all()

    def delete_mapping(self, mapping_id: int) -> bool:
        """
        Delete a name mapping.

        Args:
            mapping_id: ID of the mapping to delete

        Returns:
            True if deleted, False if not found
        """
        mapping = self.db.query(NameMapping).filter(NameMapping.id == mapping_id).first()

        if mapping:
            self.db.delete(mapping)
            self.db.commit()
            logger.info(f"Deleted mapping {mapping_id}: '{mapping.pattern}' -> '{mapping.mapped_name}'")
            return True

        return False
