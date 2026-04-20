"""
Log service implementation.
Handles all CRUD operations and analytics for browsing activity logs.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import func, desc
from server.models.base import db
from server.models.log_entry import LogEntry
from server.services.interfaces import ILogService


class LogService(ILogService):
    """Concrete implementation of log management operations."""

    def create_batch(self, logs, client_ip):
        """
        Store a batch of log entries from a client extension.

        Args:
            logs: List of log dictionaries from the extension.
            client_ip: The IP address of the reporting client.

        Returns:
            Number of successfully stored log entries.
        """
        entries = [
            LogEntry(
                url=log.get("url", ""),
                title=log.get("title"),
                video_id=log.get("video_id"),
                channel_name=log.get("channel_name"),
                channel_id=log.get("channel_id"),
                client_ip=client_ip,
                client_hostname=log.get("hostname"),
                log_type=log.get("log_type", "page_visit"),
                timestamp=_parse_timestamp(log.get("timestamp")),
            )
            for log in logs
            if log.get("url")
        ]

        db.session.bulk_save_objects(entries)
        db.session.commit()
        return len(entries)

    def get_all(self, page=1, per_page=50, filters=None):
        """
        Retrieve paginated log entries with optional filters.

        Args:
            page: Page number (1-indexed).
            per_page: Items per page.
            filters: Dictionary of filter criteria (search, log_type, client_ip, date_from, date_to).

        Returns:
            Paginated query result.
        """
        query = LogEntry.query.order_by(desc(LogEntry.timestamp))

        if filters:
            if filters.get("search"):
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    db.or_(
                        LogEntry.url.ilike(search_term),
                        LogEntry.title.ilike(search_term),
                        LogEntry.channel_name.ilike(search_term),
                    )
                )
            if filters.get("log_type"):
                query = query.filter(LogEntry.log_type == filters["log_type"])
            if filters.get("client_ip"):
                query = query.filter(LogEntry.client_ip == filters["client_ip"])
            if filters.get("date_from"):
                query = query.filter(LogEntry.timestamp >= filters["date_from"])
            if filters.get("date_to"):
                query = query.filter(LogEntry.timestamp <= filters["date_to"])

        return query.paginate(page=page, per_page=per_page, error_out=False)

    def get_top_sites(self, limit=10, days=7, date_from=None, date_to=None, hostname_prefix=None):
        """
        Get the most visited sites based on filters.

        Returns:
            List of dictionary containing url and count.
        """
        query = db.session.query(
            LogEntry.url, func.count(LogEntry.id).label("visit_count")
        ).filter(LogEntry.log_type == "page_visit")
        
        # Apply filters
        if date_from:
            try:
                dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                query = query.filter(LogEntry.timestamp >= dt_from)
            except ValueError:
                pass
        else:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(LogEntry.timestamp >= since)

        if date_to:
            try:
                dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
                query = query.filter(LogEntry.timestamp <= dt_to)
            except ValueError:
                pass

        if hostname_prefix:
            query = query.filter(LogEntry.client_hostname.ilike(f"%{hostname_prefix}%"))

        results = (
            query.group_by(LogEntry.url)
            .order_by(desc("visit_count"))
            .limit(limit)
            .all()
        )
        return [{"url": r[0], "count": r[1]} for r in results]

    def get_top_videos(self, limit=10, days=7, date_from=None, date_to=None, hostname_prefix=None):
        """
        Get the most watched YouTube videos based on filters.

        Returns:
            List of video info dictionaries with watch counts.
        """
        query = db.session.query(
            LogEntry.video_id,
            LogEntry.title,
            LogEntry.channel_name,
            func.count(LogEntry.id).label("watch_count"),
        ).filter(LogEntry.log_type == "youtube_video", LogEntry.video_id.isnot(None))

        # Apply filters
        if date_from:
            try:
                dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                query = query.filter(LogEntry.timestamp >= dt_from)
            except ValueError:
                pass
        else:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(LogEntry.timestamp >= since)

        if date_to:
            try:
                dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
                query = query.filter(LogEntry.timestamp <= dt_to)
            except ValueError:
                pass

        if hostname_prefix:
            query = query.filter(LogEntry.client_hostname.ilike(f"%{hostname_prefix}%"))

        results = (
            query.group_by(LogEntry.video_id, LogEntry.title, LogEntry.channel_name)
            .order_by(desc("watch_count"))
            .limit(limit)
            .all()
        )
        return [
            {
                "video_id": r[0],
                "title": r[1],
                "channel_name": r[2],
                "count": r[3],
            }
            for r in results
        ]

    def get_top_channels(self, limit=10, days=7, date_from=None, date_to=None, hostname_prefix=None):
        """
        Get the most watched YouTube channels based on filters.

        Returns:
            List of channel info dictionaries with watch counts.
        """
        query = db.session.query(
            LogEntry.channel_name,
            LogEntry.channel_id,
            func.count(LogEntry.id).label("watch_count"),
        ).filter(LogEntry.channel_name.isnot(None), LogEntry.channel_name != "")

        # Apply filters
        if date_from:
            try:
                dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                query = query.filter(LogEntry.timestamp >= dt_from)
            except ValueError:
                pass
        else:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(LogEntry.timestamp >= since)

        if date_to:
            try:
                dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
                query = query.filter(LogEntry.timestamp <= dt_to)
            except ValueError:
                pass

        if hostname_prefix:
            query = query.filter(LogEntry.client_hostname.ilike(f"%{hostname_prefix}%"))

        results = (
            query.group_by(LogEntry.channel_name, LogEntry.channel_id)
            .order_by(desc("watch_count"))
            .limit(limit)
            .all()
        )
        return [
            {
                "channel_name": r[0],
                "channel_id": r[1],
                "count": r[2],
            }
            for r in results
        ]

    def get_active_clients(self, minutes=30):
        """
        Get the list of client IPs that reported activity recently.

        Args:
            minutes: Time window to check for activity.

        Returns:
            List of active client info dictionaries.
        """
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        results = (
            db.session.query(
                LogEntry.client_ip,
                LogEntry.client_hostname,
                func.max(LogEntry.timestamp).label("last_seen"),
                func.count(LogEntry.id).label("log_count"),
            )
            .filter(LogEntry.timestamp >= since)
            .group_by(LogEntry.client_ip)
            .order_by(desc("last_seen"))
            .all()
        )
        return [
            {
                "client_ip": r[0],
                "hostname": r[1],
                "last_seen": r[2].isoformat() if r[2] else None,
                "log_count": r[3],
            }
            for r in results
        ]

    def get_stats(self):
        """
        Get summary statistics for the admin dashboard.

        Returns:
            Dictionary with total logs, today's logs, active clients, etc.
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total_logs = db.session.query(func.count(LogEntry.id)).scalar() or 0
        today_logs = (
            db.session.query(func.count(LogEntry.id))
            .filter(LogEntry.timestamp >= today_start)
            .scalar()
            or 0
        )
        active_clients = (
            db.session.query(func.count(func.distinct(LogEntry.client_ip)))
            .filter(LogEntry.timestamp >= now - timedelta(minutes=30))
            .scalar()
            or 0
        )
        youtube_logs = (
            db.session.query(func.count(LogEntry.id))
            .filter(
                LogEntry.video_id.isnot(None),
                LogEntry.video_id != "",
            )
            .scalar()
            or 0
        )

        return {
            "total_logs": total_logs,
            "today_logs": today_logs,
            "active_clients": active_clients,
            "youtube_logs": youtube_logs,
        }

    def delete_older_than(self, days):
        """
        Delete log entries older than the specified number of days.

        Args:
            days: Number of days to retain logs.

        Returns:
            Number of deleted entries.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        count = LogEntry.query.filter(LogEntry.timestamp < cutoff).delete()
        db.session.commit()
        return count


def _parse_timestamp(ts_value):
    """Parse a timestamp from the extension (ISO string or epoch ms)."""
    if ts_value is None:
        return datetime.now(timezone.utc)
    if isinstance(ts_value, (int, float)):
        return datetime.fromtimestamp(ts_value / 1000, tz=timezone.utc)
    try:
        return datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)
