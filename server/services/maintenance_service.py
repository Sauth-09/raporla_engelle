"""
Maintenance service implementation.
Handles database cleanup and health monitoring tasks.
"""

import os
from server.models.base import db
from server.models.log_entry import LogEntry
from server.models.app_config import AppConfig
from server.services.interfaces import IMaintenanceService


class MaintenanceService(IMaintenanceService):
    """Concrete implementation of database maintenance operations."""

    def __init__(self, config_service):
        """
        Args:
            config_service: IConfigService instance for reading retention settings.
        """
        self._config_service = config_service

    def cleanup_old_logs(self):
        """
        Delete logs older than the configured retention period.

        Returns:
            Number of deleted entries.
        """
        retention_days = int(
            self._config_service.get(AppConfig.KEY_LOG_RETENTION_DAYS, "30")
        )

        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        count = LogEntry.query.filter(LogEntry.timestamp < cutoff).delete()
        db.session.commit()
        return count

    def get_db_stats(self):
        """
        Get database size and row count statistics.

        Returns:
            Dictionary with table counts and database file size.
        """
        from server.models.blocked_item import BlockedItem
        from server.models.whitelisted_item import WhitelistedItem

        log_count = db.session.query(db.func.count(LogEntry.id)).scalar() or 0
        blocked_count = db.session.query(db.func.count(BlockedItem.id)).scalar() or 0
        whitelisted_count = db.session.query(db.func.count(WhitelistedItem.id)).scalar() or 0
        config_count = db.session.query(db.func.count(AppConfig.id)).scalar() or 0

        # Get database file size
        db_path = db.engine.url.database
        db_size_bytes = 0
        if db_path and os.path.exists(db_path):
            db_size_bytes = os.path.getsize(db_path)

        return {
            "log_entries": log_count,
            "blocked_items": blocked_count,
            "whitelisted_items": whitelisted_count,
            "config_entries": config_count,
            "db_size_bytes": db_size_bytes,
            "db_size_mb": round(db_size_bytes / (1024 * 1024), 2),
        }
