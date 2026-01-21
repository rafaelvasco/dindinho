"""Service for managing categories with fuzzy matching support."""

from typing import Optional
from sqlalchemy.orm import Session
from rapidfuzz import fuzz

from backend.models.category import Category, TransactionCategory

# Special category ID for Assinaturas (subscriptions)
SUBSCRIPTIONS_CATEGORY_ID = 1


class CategoryService:
    """Service for category management with fuzzy matching."""

    def __init__(self, db: Session):
        """
        Initialize the category service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.fuzzy_threshold = 70  # 70% match threshold

    def seed_initial_categories(self) -> list[Category]:
        """
        Seed the database with the special 'Assinaturas' category only.

        The 'Assinaturas' category is created with ID=1 and is the only default category.
        This category is special and cannot be renamed or deleted.

        Returns:
            List of created Category objects
        """
        categories = []

        # Only create the special "Assinaturas" category
        subscriptions_name = TransactionCategory.SUBSCRIPTIONS.value
        existing = self.db.query(Category).filter(Category.name == subscriptions_name).first()

        if not existing:
            # Ensure this category gets ID=1
            new_category = Category(id=1, name=subscriptions_name)
            self.db.add(new_category)
            categories.append(new_category)
            self.db.commit()

        return categories

    def find_category_by_fuzzy_match(self, category_name: str) -> Optional[Category]:
        """
        Find a category using fuzzy string matching.

        Args:
            category_name: The category name to match (AI-inferred)

        Returns:
            Category object if a match >= 70% is found, None otherwise
        """
        all_categories = self.db.query(Category).all()

        best_match = None
        best_score = 0

        for category in all_categories:
            score = fuzz.ratio(category_name.lower(), category.name.lower())
            if score > best_score:
                best_score = score
                best_match = category

        if best_score >= self.fuzzy_threshold:
            return best_match

        return None

    def find_or_create_category(self, category_name: str) -> Category:
        """
        Find an existing category by fuzzy matching or create a new one.

        This is the main method used when saving transactions:
        - Tries to find a category with >= 70% fuzzy match
        - If found, returns the existing category
        - If not found, creates a new category with the given name

        Args:
            category_name: The category name (AI-inferred)

        Returns:
            Category object (existing or newly created)
        """
        # Try fuzzy match first
        matched_category = self.find_category_by_fuzzy_match(category_name)
        if matched_category:
            return matched_category

        # No match found, create new category
        new_category = Category(name=category_name)
        self.db.add(new_category)
        self.db.commit()
        self.db.refresh(new_category)

        return new_category

    def get_all_categories(self) -> list[Category]:
        """
        Get all categories from the database.

        Returns:
            List of all Category objects
        """
        return self.db.query(Category).order_by(Category.name).all()

    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """
        Get a category by its ID.

        Args:
            category_id: The category ID

        Returns:
            Category object if found, None otherwise
        """
        return self.db.query(Category).filter(Category.id == category_id).first()

    def get_category_by_name(self, name: str) -> Optional[Category]:
        """
        Get a category by exact name match.

        Args:
            name: The exact category name

        Returns:
            Category object if found, None otherwise
        """
        return self.db.query(Category).filter(Category.name == name).first()

    def is_subscriptions_category(self, category_id: int) -> bool:
        """
        Check if a category is the special 'Assinaturas' (subscriptions) category.

        Args:
            category_id: The category ID to check

        Returns:
            True if the category is the special subscriptions category, False otherwise
        """
        return category_id == SUBSCRIPTIONS_CATEGORY_ID

    def get_subscriptions_category(self) -> Optional[Category]:
        """
        Get the special 'Assinaturas' (subscriptions) category.

        Returns:
            The subscriptions Category object or None if not found
        """
        return self.get_category_by_id(SUBSCRIPTIONS_CATEGORY_ID)
