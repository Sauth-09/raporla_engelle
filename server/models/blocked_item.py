"""
Blocked item model for managing the blacklist.
Supports URL patterns, channel IDs, video IDs, and keyword-based blocking.
"""

from datetime import datetime, timezone
from server.models.base import db


class BlockedItem(db.Model):
    """Represents a single blacklist entry for content blocking."""

    __tablename__ = "blocked_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    pattern = db.Column(db.String(1024), nullable=False)
    block_type = db.Column(
        db.String(32),
        nullable=False,
        default="keyword",
        index=True,
    )  # keyword, url, channel_id, channel_name, video_id, regex
    is_regex = db.Column(db.Boolean, nullable=False, default=False)
    description = db.Column(db.String(512), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        """Serialize blocked item to dictionary."""
        return {
            "id": self.id,
            "pattern": self.pattern,
            "block_type": self.block_type,
            "is_regex": self.is_regex,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<BlockedItem {self.id}: [{self.block_type}] {self.pattern[:40]}>"
