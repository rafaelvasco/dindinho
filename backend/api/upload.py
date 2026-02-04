"""API endpoints for CSV file upload and import."""

import logging
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.transaction_service import TransactionService
from backend.services.ai_categorizer import AICategorizer
from backend.schemas.import_preview import (
    ImportPreviewResponse,
    ImportRequest,
    ImportResult,
    IgnoredTransactionResponse,
    ImportHistoryResponse,
    ImportHistoryItem
)
from backend.models.ignored_transaction import IgnoredTransaction
from backend.models.transaction import Transaction
from sqlalchemy import func

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/preview", response_model=ImportPreviewResponse)
async def preview_csv_upload(
    file: UploadFile = File(..., description="CSV file to preview"),
    db: Session = Depends(get_db)
):
    """
    Upload CSV file and preview transactions without importing.

    Returns parsed transactions with metadata:
    - Items already in ignore list (marked for skipping)
    - Duplicate items already in database
    - New items ready to import

    The user can then review and mark items before confirming import.
    """
    logger.info(f"Previewing CSV upload: {file.filename}")

    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only CSV files are supported."
        )

    # Save uploaded file to temporary location
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Create transaction service and preview import
        transaction_service = TransactionService(db)
        preview = transaction_service.preview_csv_import(temp_file_path)

        # Clean up temp file
        Path(temp_file_path).unlink()

        logger.info(
            f"Preview generated: {preview.total_items} items, "
            f"{preview.new_count} new, {preview.ignored_count} ignored, "
            f"{preview.duplicate_count} duplicates"
        )

        return preview

    except ValueError as e:
        # CSV parsing error
        logger.error(f"CSV parsing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error during preview: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@router.post("/import", response_model=ImportResult)
async def import_csv(
    import_request: ImportRequest,
    db: Session = Depends(get_db)
):
    """
    Import transactions from CSV based on user-selected actions.

    User must first call /preview to get the parsed items, then
    submit this request with their chosen actions for each item:
    - import: Import normally with AI categorization
    - ignore_once: Skip this time only
    - ignore_always: Add to ignore list and skip
    - subscription: Create subscription and import

    Returns statistics about the import operation.
    """
    logger.info(f"Importing transactions with {len(import_request.actions)} actions")

    try:
        # Create services
        ai_categorizer = AICategorizer()
        transaction_service = TransactionService(db, ai_categorizer)

        # Perform import
        result = transaction_service.import_transactions(import_request)

        logger.info(
            f"Import completed: {result.imported_count} imported, "
            f"{result.subscriptions_created} subscriptions created, "
            f"{result.ignored_always_count} added to ignore list"
        )

        return result

    except Exception as e:
        logger.error(f"Error during import: {e}")
        raise HTTPException(status_code=500, detail=f"Error importing transactions: {str(e)}")


@router.get("/ignore-list", response_model=list[IgnoredTransactionResponse])
async def get_ignore_list(db: Session = Depends(get_db)):
    """
    Get list of all ignored transaction descriptions.

    These descriptions will be automatically skipped during CSV import
    using exact or fuzzy matching based on the threshold.
    """
    ignored = db.query(IgnoredTransaction).order_by(IgnoredTransaction.usage_count.desc()).all()
    return [
        IgnoredTransactionResponse(
            id=item.id,
            description=item.description,
            fuzzy_threshold=item.fuzzy_threshold,
            usage_count=item.usage_count,
            created_at=item.created_at.isoformat()
        )
        for item in ignored
    ]


@router.post("/ignore-list", response_model=IgnoredTransactionResponse)
async def add_to_ignore_list(
    description: str,
    fuzzy_threshold: Optional[float] = 70.0,
    db: Session = Depends(get_db)
):
    """
    Add a transaction description to the ignore list.

    Future CSV imports will automatically skip transactions that match this description
    using fuzzy matching (if threshold provided) or exact matching (if threshold is None).

    Args:
        description: Description pattern to ignore
        fuzzy_threshold: Similarity threshold (0-100). Default 70. Set to None for exact match only.
    """
    from backend.services.ignore_service import IgnoreService

    ignore_service = IgnoreService(db)
    ignored = ignore_service.add_to_ignore_list(description, fuzzy_threshold)

    return IgnoredTransactionResponse(
        id=ignored.id,
        description=ignored.description,
        fuzzy_threshold=ignored.fuzzy_threshold,
        usage_count=ignored.usage_count,
        created_at=ignored.created_at.isoformat()
    )


@router.delete("/ignore-list/{ignore_id}")
async def remove_from_ignore_list(
    ignore_id: int,
    db: Session = Depends(get_db)
):
    """
    Remove a transaction description from the ignore list.

    Future CSV imports will no longer automatically skip this description.
    """
    ignored = db.query(IgnoredTransaction).filter(IgnoredTransaction.id == ignore_id).first()

    if not ignored:
        raise HTTPException(status_code=404, detail="Ignored transaction not found")

    description = ignored.description
    db.delete(ignored)
    db.commit()

    logger.info(f"Removed from ignore list: {description}")

    return {"message": f"Removed '{description}' from ignore list"}


@router.get("/import-history", response_model=ImportHistoryResponse)
async def get_import_history(db: Session = Depends(get_db)):
    """
    Get history of imported CSV files.

    Returns a list of all imported CSV files with:
    - Source file name
    - Source type (credit_card or account_extract)
    - Number of transactions imported
    - Import date (earliest created_at for transactions from that file)
    """
    results = (
        db.query(
            Transaction.source_file,
            Transaction.source_type,
            func.count(Transaction.id).label("transaction_count"),
            func.min(Transaction.created_at).label("import_date")
        )
        .filter(Transaction.source_file.isnot(None))
        .group_by(Transaction.source_file, Transaction.source_type)
        .order_by(func.min(Transaction.created_at).desc())
        .all()
    )

    imports = [
        ImportHistoryItem(
            source_file=row.source_file,
            source_type=row.source_type,
            transaction_count=row.transaction_count,
            import_date=row.import_date
        )
        for row in results
    ]

    return ImportHistoryResponse(imports=imports)
