"""
Whitelisted item model for managing educational content that should never be blocked.
"""

from datetime import datetime, timezone
from server.models.base import db


class WhitelistedItem(db.Model):
    """Represents a single whitelist entry (e.g., educational channels)."""

    __tablename__ = "whitelisted_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    pattern = db.Column(db.String(1024), nullable=False)
    whitelist_type = db.Column(
        db.String(32),
        nullable=False,
        default="channel_id",
        index=True,
    )  # channel_id, channel_name, url, keyword
    description = db.Column(db.String(512), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        """Serialize whitelisted item to dictionary."""
        return {
            "id": self.id,
            "pattern": self.pattern,
            "whitelist_type": self.whitelist_type,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<WhitelistedItem {self.id}: [{self.whitelist_type}] {self.pattern[:40]}>"
