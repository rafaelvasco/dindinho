"""Pydantic schemas for database export/import API endpoints."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Optional, Any


class ExportMetadata(BaseModel):
    """Metadata about the exported database."""

    total_transactions: int = Field(..., description="Total number of transactions")
    total_categories: int = Field(..., description="Total number of categories")
    total_subscriptions: int = Field(..., description="Total number of subscriptions")
    total_income_sources: int = Field(..., description="Total number of income sources")
    date_range: Optional[Dict[str, str]] = Field(None, description="Date range of transactions")


class DatabaseExport(BaseModel):
    """Schema for database export."""

    version: str = Field(..., description="Export format version")
    exported_at: datetime = Field(..., description="Timestamp of export")
    schema_version: str = Field(..., description="Database schema version")
    tables: Dict[str, list] = Field(..., description="All database tables as dictionaries")
    metadata: ExportMetadata = Field(..., description="Export metadata")


class ConflictSummary(BaseModel):
    """Summary of conflicts for a specific table."""

    total: int = Field(..., description="Total records in import file")
    new: int = Field(..., description="New records to be imported")
    duplicates: int = Field(..., description="Duplicate records to be skipped")


class ImportPreview(BaseModel):
    """Preview of what will happen during import."""

    valid: bool = Field(..., description="Whether the import file is valid")
    schema_compatible: bool = Field(..., description="Whether schema versions are compatible")
    conflicts: Dict[str, ConflictSummary] = Field(..., description="Conflict summary per table")
    total_new_records: int = Field(..., description="Total new records across all tables")
    total_skipped_records: int = Field(..., description="Total skipped records across all tables")
    errors: list[str] = Field(default_factory=list, description="Validation errors if any")


class ImportRequest(BaseModel):
    """Request to import database from JSON."""

    data: Dict[str, Any] = Field(..., description="The JSON payload to import")
    create_backup: bool = Field(default=True, description="Whether to create backup before import")


class ImportResult(BaseModel):
    """Result of database import operation."""

    success: bool = Field(..., description="Whether import was successful")
    imported: Dict[str, int] = Field(..., description="Records imported per table")
    skipped: Dict[str, int] = Field(..., description="Records skipped per table")
    errors: list[str] = Field(default_factory=list, description="Errors encountered during import")
    backup_file: Optional[str] = Field(None, description="Path to backup file created before import")


class BackupInfo(BaseModel):
    """Information about a database backup."""

    filename: str = Field(..., description="Backup filename")
    filepath: str = Field(..., description="Full path to backup file")
    created_at: datetime = Field(..., description="When backup was created")
    size_bytes: int = Field(..., description="Size of backup file in bytes")


class BackupListResponse(BaseModel):
    """Response containing list of available backups."""

    backups: list[BackupInfo] = Field(..., description="List of available backups")


class BackupCreateResponse(BaseModel):
    """Response after creating a backup."""

    success: bool = Field(..., description="Whether backup was successful")
    backup_file: str = Field(..., description="Path to created backup file")
    message: str = Field(..., description="Success message")


class BackupRestoreRequest(BaseModel):
    """Request to restore from a backup."""

    backup_file: str = Field(..., description="Filename of backup to restore")


class BackupRestoreResponse(BaseModel):
    """Response after restoring from backup."""

    success: bool = Field(..., description="Whether restore was successful")
    message: str = Field(..., description="Success or error message")
