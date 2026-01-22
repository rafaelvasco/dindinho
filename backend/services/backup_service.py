"""Service for database backup and restore operations."""

import shutil
from pathlib import Path
from datetime import datetime
from typing import List
import os

from backend.config import settings
from backend.schemas.database_export import BackupInfo


class BackupService:
    """Service to handle database backups and restores."""

    def __init__(self):
        """Initialize backup service with paths."""
        self.database_path = Path(settings.DATABASE_PATH)
        self.backup_dir = self.database_path.parent / "backups"
        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> str:
        """
        Create a timestamped backup of the database.

        Returns:
            str: Full path to the created backup file

        Raises:
            FileNotFoundError: If database file doesn't exist
            IOError: If backup creation fails
        """
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.database_path}")

        # Create timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"finance.db.backup.{timestamp}"
        backup_path = self.backup_dir / backup_filename

        # Copy database file to backup location
        try:
            shutil.copy2(self.database_path, backup_path)
            return str(backup_path)
        except Exception as e:
            raise IOError(f"Failed to create backup: {str(e)}")

    def list_backups(self) -> List[BackupInfo]:
        """
        List all available backup files.

        Returns:
            List[BackupInfo]: List of backup file information, sorted by creation time (newest first)
        """
        backups = []

        if not self.backup_dir.exists():
            return backups

        # Find all backup files
        for backup_file in self.backup_dir.glob("finance.db.backup.*"):
            try:
                stat = backup_file.stat()
                backups.append(
                    BackupInfo(
                        filename=backup_file.name,
                        filepath=str(backup_file),
                        created_at=datetime.fromtimestamp(stat.st_mtime),
                        size_bytes=stat.st_size
                    )
                )
            except Exception:
                # Skip files that can't be read
                continue

        # Sort by creation time, newest first
        backups.sort(key=lambda x: x.created_at, reverse=True)
        return backups

    def restore_backup(self, backup_file: str) -> None:
        """
        Restore database from a backup file.

        Args:
            backup_file: Filename of the backup to restore (just the filename, not full path)

        Raises:
            FileNotFoundError: If backup file doesn't exist
            IOError: If restore operation fails
        """
        backup_path = self.backup_dir / backup_file

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")

        # Create a safety backup of current database before restore
        if self.database_path.exists():
            safety_backup = self.database_path.parent / f"finance.db.before_restore.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                shutil.copy2(self.database_path, safety_backup)
            except Exception as e:
                raise IOError(f"Failed to create safety backup: {str(e)}")

        # Restore backup
        try:
            shutil.copy2(backup_path, self.database_path)
        except Exception as e:
            raise IOError(f"Failed to restore backup: {str(e)}")

    def cleanup_old_backups(self, keep: int = 5) -> int:
        """
        Remove old backups, keeping only the most recent ones.

        Args:
            keep: Number of most recent backups to keep (default: 5)

        Returns:
            int: Number of backups deleted
        """
        backups = self.list_backups()

        if len(backups) <= keep:
            return 0

        # Delete old backups beyond the keep limit
        deleted_count = 0
        for backup in backups[keep:]:
            try:
                backup_path = Path(backup.filepath)
                backup_path.unlink()
                deleted_count += 1
            except Exception:
                # Skip files that can't be deleted
                continue

        return deleted_count

    def get_backup_path(self, backup_file: str) -> Path:
        """
        Get the full path to a backup file.

        Args:
            backup_file: Filename of the backup

        Returns:
            Path: Full path to the backup file
        """
        return self.backup_dir / backup_file
