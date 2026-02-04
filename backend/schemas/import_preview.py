"""Pydantic schemas for CSV import preview and import process."""

from pydantic import BaseModel, Field
from datetime import date as DateType, datetime
from typing import Optional, Literal, List


class PreviewTransactionItem(BaseModel):
    """Schema for a single transaction item in the preview."""

    index: int = Field(..., description="Row index in the CSV")
    date: DateType = Field(..., description="Transaction date")
    description: str = Field(..., description="Transaction description")
    amount: float = Field(..., ge=0, description="Transaction amount (absolute value)")
    transaction_type: Literal['EXPENSE', 'INCOME', 'PAYMENT', 'REFUND'] = Field(..., description="Transaction type")
    original_category: Optional[str] = Field(None, description="Original category from CSV")
    source_type: str = Field(..., description="Source type: 'credit_card' or 'account_extract'")
    is_ignored: bool = Field(default=False, description="Whether this item is in the ignore list")
    is_duplicate: bool = Field(default=False, description="Whether this item already exists in database")
    existing_transaction_id: Optional[int] = Field(None, description="ID of existing transaction if duplicate")
    suggested_name: Optional[str] = Field(None, description="Suggested mapped name based on fuzzy matching")


class ImportPreviewResponse(BaseModel):
    """Schema for CSV import preview response."""

    source_type: str = Field(..., description="Detected source type")
    total_items: int = Field(..., description="Total number of items parsed")
    ignored_count: int = Field(..., description="Number of items in ignore list")
    duplicate_count: int = Field(..., description="Number of duplicate items")
    new_count: int = Field(..., description="Number of new items to import")
    items: list[PreviewTransactionItem] = Field(..., description="List of parsed transaction items")


class ItemAction(BaseModel):
    """Schema for user action on a single transaction item during import."""

    index: int = Field(..., description="Row index (matches PreviewTransactionItem.index)")
    action: Literal["import", "ignore_once", "ignore_always", "subscription", "overwrite"] = Field(
        ...,
        description=(
            "Action to take: "
            "'import' = import normally, "
            "'ignore_once' = skip this time only, "
            "'ignore_always' = add to ignore list and skip, "
            "'subscription' = create subscription and import, "
            "'overwrite' = overwrite existing duplicate transaction"
        )
    )
    edited_description: Optional[str] = Field(
        None,
        description="Edited description (if user modified the original description)"
    )
    subscription_name: Optional[str] = Field(
        None,
        description="Subscription name (required if action='subscription')"
    )


class ImportRequest(BaseModel):
    """Schema for CSV import request with user-selected actions."""

    source_file: str = Field(..., description="Source CSV filename")
    source_type: str = Field(..., description="Source type: 'credit_card' or 'account_extract'")
    items: list[PreviewTransactionItem] = Field(..., description="All parsed items from preview")
    actions: list[ItemAction] = Field(..., description="User-selected actions for each item")


class ImportResult(BaseModel):
    """Schema for import operation result."""

    total_processed: int = Field(..., description="Total items processed")
    imported_count: int = Field(..., description="Number of transactions imported")
    ignored_once_count: int = Field(..., description="Number of items ignored this time")
    ignored_always_count: int = Field(..., description="Number of items added to ignore list")
    subscriptions_created: int = Field(..., description="Number of subscriptions created")
    overwritten_count: int = Field(default=0, description="Number of transactions overwritten")
    errors: list[str] = Field(default_factory=list, description="List of error messages")


class IgnoredTransactionResponse(BaseModel):
    """Schema for ignored transaction API response."""

    id: int
    description: str
    fuzzy_threshold: Optional[float] = Field(None, description="Fuzzy matching threshold (None for exact match)")
    usage_count: int = Field(default=0, description="Number of times this rule has been used")
    created_at: str

    class Config:
        from_attributes = True


class ImportHistoryItem(BaseModel):
    """Schema for a single import history item."""

    source_file: str = Field(..., description="Name of the imported CSV file")
    source_type: str = Field(..., description="Source type: 'credit_card' or 'account_extract'")
    transaction_count: int = Field(..., description="Number of transactions imported from this file")
    import_date: datetime = Field(..., description="Date and time when the file was imported")


class ImportHistoryResponse(BaseModel):
    """Schema for import history response."""

    imports: List[ImportHistoryItem] = Field(..., description="List of imported files with metadata")
