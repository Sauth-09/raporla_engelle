"""
Application configuration model for storing runtime settings as key-value pairs.
Enables remote configuration of the extension fleet from the admin panel.
"""

from datetime import datetime, timezone
from server.models.base import db


class AppConfig(db.Model):
    """Key-value store for application-wide runtime settings."""

    __tablename__ = "app_config"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(128), nullable=False, unique=True, index=True)
    value = db.Column(db.String(1024), nullable=False)
    description = db.Column(db.String(512), nullable=True)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Well-known configuration keys
    KEY_SYNC_INTERVAL = "sync_interval_minutes"
    KEY_KILL_SWITCH = "kill_switch_enabled"
    KEY_LOG_RETENTION_DAYS = "log_retention_days"
    KEY_ADMIN_PASSWORD_CHANGED = "admin_password_changed"
    KEY_BLOCK_MESSAGE = "block_message"

    def to_dict(self):
        """Serialize config entry to dictionary."""
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<AppConfig {self.key}={self.value}>"
