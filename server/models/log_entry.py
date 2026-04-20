"""
Log entry model for storing browsing activity reported by client extensions.
"""

from datetime import datetime, timezone
from server.models.base import db


class LogEntry(db.Model):
    """Represents a single browsing activity log from a client device."""

    __tablename__ = "log_entries"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    url = db.Column(db.String(2048), nullable=False)
    title = db.Column(db.String(512), nullable=True)
    video_id = db.Column(db.String(32), nullable=True, index=True)
    channel_name = db.Column(db.String(256), nullable=True)
    channel_id = db.Column(db.String(64), nullable=True)
    client_ip = db.Column(db.String(45), nullable=False, index=True)
    client_hostname = db.Column(db.String(256), nullable=True)
    log_type = db.Column(db.String(32), nullable=False, default="page_visit")
    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def to_dict(self):
        """Serialize log entry to dictionary."""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "video_id": self.video_id,
            "channel_name": self.channel_name,
            "channel_id": self.channel_id,
            "client_ip": self.client_ip,
            "client_hostname": self.client_hostname,
            "log_type": self.log_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self):
        return f"<LogEntry {self.id}: {self.url[:50]}>"
