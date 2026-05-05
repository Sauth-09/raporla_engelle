"""
Service interfaces (Abstract Base Classes).
All services are accessed through these interfaces to enable
dependency injection and testability.
"""

from abc import ABC, abstractmethod
from typing import Optional


class ILogService(ABC):
    """Interface for log management operations."""

    @abstractmethod
    def create_batch(self, logs, client_ip):
        """Store a batch of log entries from a client."""
        ...

    @abstractmethod
    def get_all(self, page=1, per_page=50, filters=None):
        """Retrieve paginated log entries with optional filters."""
        ...

    @abstractmethod
    def get_top_sites(self, limit=10, days=7):
        """Get the most visited sites within a time range."""
        ...

    @abstractmethod
    def get_top_videos(self, limit=10, days=7):
        """Get the most watched YouTube videos within a time range."""
        ...

    @abstractmethod
    def get_active_clients(self, minutes=30):
        """Get list of recently active client IPs."""
        ...

    @abstractmethod
    def get_stats(self):
        """Get summary statistics for the dashboard."""
        ...

    @abstractmethod
    def delete_older_than(self, days):
        """Delete log entries older than the specified number of days."""
        ...

    @abstractmethod
    def delete_all_logs(self):
        """Delete all log entries."""
        ...

    @abstractmethod
    def delete_client_logs(self, hostname):
        """Delete all log entries for a specific client hostname."""
        ...

    @abstractmethod
    def get_video_detail(self, video_id):
        """Get detailed info about a video: which clients watched it and when."""
        ...

    @abstractmethod
    def get_client_activity(self, hostname, page=1, per_page=50, log_type=None, date_from=None, date_to=None):
        """Get paginated activity logs for a specific client hostname."""
        ...

    @abstractmethod
    def get_all_clients(self):
        """Get a list of all known client hostnames with stats."""
        ...

    @abstractmethod
    def get_client_top_videos(self, hostname, limit=10):
        """Get top videos for a specific client."""
        ...

    @abstractmethod
    def get_client_top_sites(self, hostname, limit=10):
        """Get top sites for a specific client."""
        ...


class IBlocklistService(ABC):
    """Interface for blacklist/whitelist management."""

    @abstractmethod
    def get_blocked_items(self, active_only=True):
        """Get all blocked items, optionally filtered by active status."""
        ...

    @abstractmethod
    def add_blocked_item(self, pattern, block_type, is_regex=False, description=None):
        """Add a new item to the blacklist."""
        ...

    @abstractmethod
    def remove_blocked_item(self, item_id):
        """Remove an item from the blacklist."""
        ...

    @abstractmethod
    def toggle_blocked_item(self, item_id):
        """Toggle the active status of a blocked item."""
        ...

    @abstractmethod
    def get_whitelisted_items(self, active_only=True):
        """Get all whitelisted items."""
        ...

    @abstractmethod
    def add_whitelisted_item(self, pattern, whitelist_type, description=None):
        """Add a new item to the whitelist."""
        ...

    @abstractmethod
    def remove_whitelisted_item(self, item_id):
        """Remove an item from the whitelist."""
        ...

    @abstractmethod
    def toggle_whitelisted_item(self, item_id):
        """Toggle the active status of a whitelisted item."""
        ...

    @abstractmethod
    def get_blocklist_for_extension(self):
        """Get combined blocklist data formatted for the extension."""
        ...


class IConfigService(ABC):
    """Interface for application configuration management."""

    @abstractmethod
    def get(self, key, default=None):
        """Get a configuration value by key."""
        ...

    @abstractmethod
    def set(self, key, value, description=None):
        """Set a configuration value."""
        ...

    @abstractmethod
    def get_extension_config(self):
        """Get all configuration values needed by the extension."""
        ...

    @abstractmethod
    def get_all(self):
        """Get all configuration entries."""
        ...

    @abstractmethod
    def initialize_defaults(self, app_config):
        """Initialize default configuration values if they don't exist."""
        ...


class IMaintenanceService(ABC):
    """Interface for database maintenance operations."""

    @abstractmethod
    def cleanup_old_logs(self):
        """Delete logs older than the configured retention period."""
        ...

    @abstractmethod
    def get_db_stats(self):
        """Get database size and row count statistics."""
        ...
