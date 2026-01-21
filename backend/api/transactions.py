"""API endpoints for transaction CRUD operations."""

import logging
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.transaction_service import TransactionService
from backend.schemas.transaction import (
    TransactionResponse,
    TransactionListResponse,
    TransactionUpdate,
    TransactionCreate
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new transaction manually.

    This allows creating transactions that don't come from CSV imports.
    """
    from backend.models.transaction import Transaction, TransactionType
    from backend.services.category_service import CategoryService

    try:
        # Get or create category
        category_service = CategoryService(db)
        category = category_service.find_or_create_category(transaction.category)

        # Convert transaction type string to enum
        txn_type = TransactionType[transaction.transaction_type.upper()]

        # Create transaction
        new_transaction = Transaction(
            date=transaction.date,
            description=transaction.description,
            amount=transaction.amount,
            currency=transaction.currency,
            transaction_type=txn_type,
            original_category=transaction.original_category,
            category_id=category.id,
            source_type=transaction.source_type,
            source_file=transaction.source_file,
            raw_data=transaction.raw_data,
            subscription_id=transaction.subscription_id
        )

        db.add(new_transaction)
        db.commit()
        db.refresh(new_transaction)

        logger.info(f"Created transaction manually: {new_transaction.id}")

        return TransactionResponse(
            id=new_transaction.id,
            date=new_transaction.date,
            description=new_transaction.description,
            amount=new_transaction.amount,
            currency=new_transaction.currency,
            original_category=new_transaction.original_category,
            category=new_transaction.category.name if new_transaction.category else "Unknown",
            category_id=new_transaction.category_id,
            transaction_type=new_transaction.transaction_type.value if new_transaction.transaction_type else None,
            source_type=new_transaction.source_type,
            source_file=new_transaction.source_file,
            subscription_id=new_transaction.subscription_id,
            income_source_id=new_transaction.income_source_id,
            created_at=new_transaction.created_at,
            updated_at=new_transaction.updated_at
        )

    except Exception as e:
        logger.error(f"Error creating transaction: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=TransactionListResponse)
async def get_transactions(
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in description"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """
    Get list of transactions with optional filters.

    Supports pagination and filtering by:
    - Date range (start_date, end_date)
    - Category
    - Description search

    Returns paginated list with total count.
    """
    transaction_service = TransactionService(db)

    transactions, total = transaction_service.get_transactions(
        start_date=start_date,
        end_date=end_date,
        category=category,
        search=search,
        limit=limit,
        offset=offset
    )

    # Convert to response schema
    transaction_responses = [
        TransactionResponse(
            id=txn.id,
            date=txn.date,
            description=txn.description,
            amount=txn.amount,
            currency=txn.currency,
            original_category=txn.original_category,
            category=txn.category.name if txn.category else "Unknown",
            category_id=txn.category_id,
            transaction_type=txn.transaction_type.value if txn.transaction_type else None,
            source_type=txn.source_type,
            source_file=txn.source_file,
            subscription_id=txn.subscription_id,
            income_source_id=txn.income_source_id,
            created_at=txn.created_at,
            updated_at=txn.updated_at
        )
        for txn in transactions
    ]

    return TransactionListResponse(
        total=total,
        transactions=transaction_responses
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a single transaction by ID.
    """
    from backend.models.transaction import Transaction

    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return TransactionResponse(
        id=transaction.id,
        date=transaction.date,
        description=transaction.description,
        amount=transaction.amount,
        currency=transaction.currency,
        original_category=transaction.original_category,
        category=transaction.category.name if transaction.category else "Unknown",
        category_id=transaction.category_id,
        transaction_type=transaction.transaction_type.value if transaction.transaction_type else None,
        source_type=transaction.source_type,
        source_file=transaction.source_file,
        subscription_id=transaction.subscription_id,
        income_source_id=transaction.income_source_id,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at
    )


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    transaction_update: TransactionUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a transaction.

    Allows updating:
    - category: Change the transaction category
    - description: Change the transaction description
    - subscription_id: Link to a different subscription
    """
    transaction_service = TransactionService(db)

    # Get existing transaction
    from backend.models.transaction import Transaction
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Update category if provided
    if transaction_update.category is not None:
        try:
            transaction = transaction_service.update_transaction_category(transaction_id, transaction_update.category)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Update description if provided
    if transaction_update.description is not None:
        transaction.description = transaction_update.description
        db.commit()
        db.refresh(transaction)

    # Update subscription if provided
    if transaction_update.subscription_id is not None:
        from backend.services.category_service import SUBSCRIPTIONS_CATEGORY_ID

        # If linking to a subscription, ensure category is Assinaturas
        if transaction_update.subscription_id > 0:
            transaction.subscription_id = transaction_update.subscription_id
            transaction.category_id = SUBSCRIPTIONS_CATEGORY_ID
        # If unlinking from subscription (setting to None/0), category can be changed later
        else:
            transaction.subscription_id = None

        db.commit()
        db.refresh(transaction)

    # Update income source if provided
    if transaction_update.income_source_id is not None:
        from backend.models.transaction import TransactionType

        # If linking to an income source, validate transaction type
        if transaction_update.income_source_id > 0:
            if transaction.transaction_type != TransactionType.INCOME:
                raise HTTPException(
                    status_code=400,
                    detail=f"Only INCOME transactions can be linked to income sources. "
                           f"This transaction is type {transaction.transaction_type.value}"
                )
            transaction.income_source_id = transaction_update.income_source_id
        # If unlinking from income source (setting to None/0)
        else:
            transaction.income_source_id = None

        db.commit()
        db.refresh(transaction)

    logger.info(f"Updated transaction {transaction_id}")

    return TransactionResponse(
        id=transaction.id,
        date=transaction.date,
        description=transaction.description,
        amount=transaction.amount,
        currency=transaction.currency,
        original_category=transaction.original_category,
        category=transaction.category.name if transaction.category else "Unknown",
        category_id=transaction.category_id,
        transaction_type=transaction.transaction_type.value if transaction.transaction_type else None,
        source_type=transaction.source_type,
        source_file=transaction.source_file,
        subscription_id=transaction.subscription_id,
        income_source_id=transaction.income_source_id,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at
    )


@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a transaction.

    If the transaction is linked to a subscription, it will be unlinked first.
    """
    transaction_service = TransactionService(db)

    deleted = transaction_service.delete_transaction(transaction_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")

    logger.info(f"Deleted transaction {transaction_id}")

    return {"message": f"Transaction {transaction_id} deleted successfully"}
