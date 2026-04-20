"""
Configuration service implementation.
Manages runtime application settings stored in the database
and provides extension-facing configuration endpoints.
"""

from server.models.base import db
from server.models.app_config import AppConfig
from server.services.interfaces import IConfigService


class ConfigService(IConfigService):
    """Concrete implementation of configuration management."""

    def get(self, key, default=None):
        """
        Get a configuration value by key.

        Args:
            key: Configuration key name.
            default: Default value if key not found.

        Returns:
            The configuration value as a string, or default.
        """
        entry = AppConfig.query.filter_by(key=key).first()
        return entry.value if entry else default

    def set(self, key, value, description=None):
        """
        Set a configuration value (upsert).

        Args:
            key: Configuration key name.
            value: Configuration value (will be stored as string).
            description: Optional description of the setting.

        Returns:
            The updated or created AppConfig entry.
        """
        entry = AppConfig.query.filter_by(key=key).first()
        if entry:
            entry.value = str(value)
            if description is not None:
                entry.description = description
        else:
            entry = AppConfig(
                key=key,
                value=str(value),
                description=description,
            )
            db.session.add(entry)

        db.session.commit()
        return entry

    def get_extension_config(self):
        """
        Get all configuration values needed by the Chrome extension.

        Returns:
            Dictionary with sync_interval, kill_switch, and block_message.
        """
        return {
            "sync_interval_minutes": int(
                self.get(AppConfig.KEY_SYNC_INTERVAL, "5")
            ),
            "kill_switch_enabled": self.get(
                AppConfig.KEY_KILL_SWITCH, "false"
            ).lower() == "true",
            "block_message": self.get(
                AppConfig.KEY_BLOCK_MESSAGE,
                "Bu içerik okul yönetimi tarafından engellenmiştir.",
            ),
        }

    def get_all(self):
        """Get all configuration entries."""
        return AppConfig.query.order_by(AppConfig.key).all()

    def initialize_defaults(self, app_config):
        """
        Initialize default configuration values if they don't exist.
        Called during application startup.

        Args:
            app_config: Flask app configuration object.
        """
        defaults = [
            (
                AppConfig.KEY_SYNC_INTERVAL,
                str(app_config.DEFAULT_SYNC_INTERVAL_MINUTES),
                "Extension sync interval in minutes",
            ),
            (
                AppConfig.KEY_KILL_SWITCH,
                str(app_config.DEFAULT_KILL_SWITCH).lower(),
                "Global kill switch - disables all blocking when true",
            ),
            (
                AppConfig.KEY_LOG_RETENTION_DAYS,
                str(app_config.DEFAULT_LOG_RETENTION_DAYS),
                "Number of days to retain log entries",
            ),
            (
                AppConfig.KEY_ADMIN_PASSWORD_CHANGED,
                "false",
                "Whether the default admin password has been changed",
            ),
            (
                AppConfig.KEY_BLOCK_MESSAGE,
                "Bu video kullanılamıyor.",
                "Message shown when content is blocked",
            ),
        ]

        for key, value, description in defaults:
            existing = AppConfig.query.filter_by(key=key).first()
            if not existing:
                db.session.add(
                    AppConfig(key=key, value=value, description=description)
                )

        db.session.commit()
