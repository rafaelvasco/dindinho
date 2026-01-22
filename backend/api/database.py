"""API endpoints for database import/export and backup operations."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.database_export_service import DatabaseExportService
from backend.services.database_import_service import DatabaseImportService
from backend.services.backup_service import BackupService
from backend.services.database_clear_service import DatabaseClearService
from backend.schemas.database_export import (
    ImportPreview,
    ImportRequest,
    ImportResult,
    BackupListResponse,
    BackupCreateResponse,
    BackupRestoreRequest,
    BackupRestoreResponse,
    ClearDatabaseRequest,
    ClearDatabaseResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/export")
async def export_database(db: Session = Depends(get_db)) -> JSONResponse:
    """
    Export entire database to JSON format.

    Returns:
        JSON file with all database tables and metadata
    """
    try:
        logger.info("Starting database export")
        export_data = DatabaseExportService.export_to_json(db)
        logger.info("Database export completed successfully")

        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": f"attachment; filename=dindinho_export_{export_data['exported_at']}.json"
            }
        )
    except Exception as e:
        logger.error(f"Database export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/import/preview", response_model=ImportPreview)
async def preview_database_import(
    import_data: Dict[str, Any],
    db: Session = Depends(get_db)
) -> ImportPreview:
    """
    Preview database import to see what will be imported and what will be skipped.

    Args:
        import_data: The JSON export data to preview

    Returns:
        ImportPreview with conflict analysis
    """
    try:
        logger.info("Previewing database import")
        preview = DatabaseImportService.preview_import(db, import_data)
        logger.info(
            f"Import preview: {preview.total_new_records} new, "
            f"{preview.total_skipped_records} skipped"
        )
        return preview
    except Exception as e:
        logger.error(f"Import preview failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/import/execute", response_model=ImportResult)
async def execute_database_import(
    request: ImportRequest,
    db: Session = Depends(get_db)
) -> ImportResult:
    """
    Execute database import with "skip duplicates" strategy.

    Args:
        request: Import request with data and options

    Returns:
        ImportResult with statistics
    """
    backup_file = None

    try:
        # Create backup before import if requested
        if request.create_backup:
            logger.info("Creating backup before import")
            backup_service = BackupService()
            backup_file = backup_service.create_backup()
            logger.info(f"Backup created: {backup_file}")

        # Execute import
        logger.info("Starting database import")
        result = DatabaseImportService.execute_import(db, request.data)

        if result.success:
            logger.info(
                f"Database import completed successfully: "
                f"{sum(result.imported.values())} imported, "
                f"{sum(result.skipped.values())} skipped"
            )
            # Cleanup old backups, keep last 5
            if request.create_backup:
                backup_service.cleanup_old_backups(keep=5)
        else:
            logger.error(f"Database import failed: {result.errors}")

        # Add backup file to result
        result.backup_file = backup_file
        return result

    except Exception as e:
        logger.error(f"Database import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/backup/create", response_model=BackupCreateResponse)
async def create_backup() -> BackupCreateResponse:
    """
    Create a manual backup of the database.

    Returns:
        BackupCreateResponse with backup file path
    """
    try:
        logger.info("Creating manual database backup")
        backup_service = BackupService()
        backup_file = backup_service.create_backup()
        logger.info(f"Manual backup created: {backup_file}")

        return BackupCreateResponse(
            success=True,
            backup_file=backup_file,
            message="Backup created successfully"
        )
    except Exception as e:
        logger.error(f"Backup creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")


@router.get("/backup/list", response_model=BackupListResponse)
async def list_backups() -> BackupListResponse:
    """
    List all available database backups.

    Returns:
        BackupListResponse with list of backups
    """
    try:
        backup_service = BackupService()
        backups = backup_service.list_backups()
        logger.info(f"Listed {len(backups)} backups")

        return BackupListResponse(backups=backups)
    except Exception as e:
        logger.error(f"Failed to list backups: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")


@router.post("/backup/restore", response_model=BackupRestoreResponse)
async def restore_backup(request: BackupRestoreRequest) -> BackupRestoreResponse:
    """
    Restore database from a backup file.

    Args:
        request: Restore request with backup filename

    Returns:
        BackupRestoreResponse with result
    """
    try:
        logger.info(f"Restoring database from backup: {request.backup_file}")
        backup_service = BackupService()
        backup_service.restore_backup(request.backup_file)
        logger.info("Database restored successfully")

        return BackupRestoreResponse(
            success=True,
            message=f"Database restored successfully from {request.backup_file}"
        )
    except FileNotFoundError as e:
        logger.error(f"Backup file not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Database restore failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@router.post("/clear", response_model=ClearDatabaseResponse)
async def clear_database(
    request: ClearDatabaseRequest,
    db: Session = Depends(get_db)
) -> ClearDatabaseResponse:
    """
    Clear all data from the database.

    **DANGER:** This operation deletes all data from all tables.
    A backup is strongly recommended before proceeding.

    Args:
        request: Clear request with confirmation and backup option
        db: Database session

    Returns:
        ClearDatabaseResponse with result
    """
    # Require exact confirmation text
    if request.confirmation_text != "DELETE ALL DATA":
        raise HTTPException(
            status_code=400,
            detail="Invalid confirmation text. You must type 'DELETE ALL DATA' exactly."
        )

    backup_file = None

    try:
        # Create backup before clearing if requested
        if request.create_backup:
            logger.info("Creating backup before clearing database")
            backup_service = BackupService()
            backup_file = backup_service.create_backup()
            logger.info(f"Backup created: {backup_file}")

        # Clear database
        logger.warning("CLEARING ALL DATABASE DATA")
        records_deleted = DatabaseClearService.clear_all_data(db)
        logger.info(f"Database cleared: {records_deleted}")

        total_deleted = sum(records_deleted.values())

        return ClearDatabaseResponse(
            success=True,
            message=f"Database cleared successfully. {total_deleted} records deleted.",
            backup_file=backup_file,
            records_deleted=records_deleted
        )

    except Exception as e:
        logger.error(f"Database clear failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Clear failed: {str(e)}")
