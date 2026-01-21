"""API endpoints for category management."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.models.category import Category
from backend.services.category_service import CategoryService

logger = logging.getLogger(__name__)

router = APIRouter()


class CategoryResponse(BaseModel):
    """Schema for category API responses."""

    id: int
    name: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""

    name: str = Field(..., min_length=1, description="Category name")


@router.get("", response_model=List[CategoryResponse])
async def get_all_categories(db: Session = Depends(get_db)):
    """
    Get all categories.

    Returns list of all categories ordered by name.
    """
    category_service = CategoryService(db)
    categories = category_service.get_all_categories()

    return [
        CategoryResponse(
            id=cat.id,
            name=cat.name,
            created_at=cat.created_at.isoformat(),
            updated_at=cat.updated_at.isoformat()
        )
        for cat in categories
    ]


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int, db: Session = Depends(get_db)):
    """
    Get a single category by ID.
    """
    category_service = CategoryService(db)
    category = category_service.get_category_by_id(category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return CategoryResponse(
        id=category.id,
        name=category.name,
        created_at=category.created_at.isoformat(),
        updated_at=category.updated_at.isoformat()
    )


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a category's name.

    This will affect all expenses linked to this category.
    Note: The special 'Assinaturas' category (ID=1) cannot be renamed.
    """
    category_service = CategoryService(db)

    # Prevent renaming the special subscriptions category
    if category_service.is_subscriptions_category(category_id):
        raise HTTPException(
            status_code=403,
            detail="The 'Assinaturas' category is special and cannot be renamed"
        )

    # Get existing category
    category = category_service.get_category_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if new name already exists (case-insensitive)
    existing = db.query(Category).filter(
        Category.name.ilike(category_update.name),
        Category.id != category_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Category with name '{category_update.name}' already exists"
        )

    # Update category name
    category.name = category_update.name
    db.commit()
    db.refresh(category)

    logger.info(f"Updated category {category_id} to '{category_update.name}'")

    return CategoryResponse(
        id=category.id,
        name=category.name,
        created_at=category.created_at.isoformat(),
        updated_at=category.updated_at.isoformat()
    )


@router.delete("/{category_id}")
async def delete_category(category_id: int, db: Session = Depends(get_db)):
    """
    Delete a category.

    Note: The special 'Assinaturas' category (ID=1) cannot be deleted.
    Also, categories with linked expenses cannot be deleted.
    """
    category_service = CategoryService(db)

    # Prevent deleting the special subscriptions category
    if category_service.is_subscriptions_category(category_id):
        raise HTTPException(
            status_code=403,
            detail="The 'Assinaturas' category is special and cannot be deleted"
        )

    # Get category
    category = category_service.get_category_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check if category has linked expenses
    if category.expenses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category '{category.name}' because it has {len(category.expenses)} linked expense(s)"
        )

    # Delete category
    db.delete(category)
    db.commit()

    logger.info(f"Deleted category {category_id} ('{category.name}')")

    return {"message": f"Category '{category.name}' deleted successfully"}
