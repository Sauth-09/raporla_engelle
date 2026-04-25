"""
Log service implementation.
Handles all CRUD operations and analytics for browsing activity logs.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import func, desc, case
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

    def get_video_detail(self, video_id):
        """
        Get detailed information about a specific video:
        basic info, total watch count, and per-client breakdown.

        Args:
            video_id: YouTube video ID.

        Returns:
            Dictionary with video info and per-client watch data.
        """
        # Basic video info (latest entry)
        latest = (
            LogEntry.query
            .filter(LogEntry.video_id == video_id)
            .order_by(desc(LogEntry.timestamp))
            .first()
        )

        if not latest:
            return None

        # Total watch count
        total_count = (
            db.session.query(func.count(LogEntry.id))
            .filter(LogEntry.video_id == video_id)
            .scalar() or 0
        )

        # Per-client breakdown (which classes/devices watched)
        client_breakdown = (
            db.session.query(
                LogEntry.client_hostname,
                LogEntry.client_ip,
                func.count(LogEntry.id).label("watch_count"),
                func.min(LogEntry.timestamp).label("first_watched"),
                func.max(LogEntry.timestamp).label("last_watched"),
            )
            .filter(LogEntry.video_id == video_id)
            .group_by(LogEntry.client_hostname, LogEntry.client_ip)
            .order_by(desc("watch_count"))
            .all()
        )

        # Timeline: recent watch events
        recent_watches = (
            LogEntry.query
            .filter(LogEntry.video_id == video_id)
            .order_by(desc(LogEntry.timestamp))
            .limit(50)
            .all()
        )

        return {
            "video_id": video_id,
            "title": latest.title or "Başlıksız",
            "channel_name": latest.channel_name or "Bilinmeyen Kanal",
            "total_count": total_count,
            "clients": [
                {
                    "hostname": r[0] or "Bilinmiyor",
                    "client_ip": r[1],
                    "watch_count": r[2],
                    "first_watched": r[3].isoformat() if r[3] else None,
                    "last_watched": r[4].isoformat() if r[4] else None,
                }
                for r in client_breakdown
            ],
            "recent_watches": [
                {
                    "hostname": w.client_hostname or "Bilinmiyor",
                    "client_ip": w.client_ip,
                    "timestamp": w.timestamp.isoformat() if w.timestamp else None,
                }
                for w in recent_watches
            ],
        }

    def get_client_activity(self, hostname, page=1, per_page=50, log_type=None, date_from=None, date_to=None):
        """
        Get paginated activity logs for a specific client hostname.

        Args:
            hostname: The client_hostname to filter by.
            page: Page number.
            per_page: Items per page.
            log_type: Optional log type filter.
            date_from: Optional start date string (YYYY-MM-DD).
            date_to: Optional end date string (YYYY-MM-DD).

        Returns:
            Paginated query result.
        """
        query = (
            LogEntry.query
            .filter(LogEntry.client_hostname == hostname)
            .order_by(desc(LogEntry.timestamp))
        )

        if log_type and log_type != "all":
            query = query.filter(LogEntry.log_type == log_type)

        if date_from:
            try:
                dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                query = query.filter(LogEntry.timestamp >= dt_from)
            except ValueError:
                pass

        if date_to:
            try:
                dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
                query = query.filter(LogEntry.timestamp <= dt_to)
            except ValueError:
                pass

        return query.paginate(page=page, per_page=per_page, error_out=False)

    def get_all_clients(self):
        """
        Get a list of all known client hostnames with aggregated stats.

        Returns:
            List of client info dictionaries sorted by last_seen descending.
        """
        now = datetime.utcnow()
        since_30min = now - timedelta(minutes=30)

        results = (
            db.session.query(
                LogEntry.client_hostname,
                LogEntry.client_ip,
                func.count(LogEntry.id).label("total_logs"),
                func.count(
                    case(
                        (LogEntry.log_type == "youtube_video", LogEntry.id),
                    )
                ).label("youtube_count"),
                func.count(
                    case(
                        (LogEntry.log_type == "page_visit", LogEntry.id),
                    )
                ).label("page_visit_count"),
                func.max(LogEntry.timestamp).label("last_seen"),
                func.min(LogEntry.timestamp).label("first_seen"),
            )
            .filter(
                LogEntry.client_hostname.isnot(None),
                LogEntry.client_hostname != "",
                LogEntry.log_type != "heartbeat",
            )
            .group_by(LogEntry.client_hostname)
            .order_by(desc("last_seen"))
            .all()
        )

        return [
            {
                "hostname": r[0],
                "client_ip": r[1],
                "total_logs": r[2],
                "youtube_count": r[3],
                "page_visit_count": r[4],
                "last_seen": r[5].isoformat() if r[5] else None,
                "first_seen": r[6].isoformat() if r[6] else None,
                "is_online": r[5] >= since_30min if r[5] else False,
            }
            for r in results
        ]

    def get_client_top_videos(self, hostname, limit=10):
        """
        Get top watched videos for a specific client hostname.

        Args:
            hostname: Client hostname to filter.
            limit: Maximum results.

        Returns:
            List of video info dictionaries.
        """
        results = (
            db.session.query(
                LogEntry.video_id,
                LogEntry.title,
                LogEntry.channel_name,
                func.count(LogEntry.id).label("watch_count"),
                func.max(LogEntry.timestamp).label("last_watched"),
            )
            .filter(
                LogEntry.client_hostname == hostname,
                LogEntry.log_type == "youtube_video",
                LogEntry.video_id.isnot(None),
            )
            .group_by(LogEntry.video_id, LogEntry.title, LogEntry.channel_name)
            .order_by(desc("watch_count"))
            .limit(limit)
            .all()
        )

        return [
            {
                "video_id": r[0],
                "title": r[1] or "Başlıksız",
                "channel_name": r[2] or "Bilinmeyen Kanal",
                "count": r[3],
                "last_watched": r[4].isoformat() if r[4] else None,
            }
            for r in results
        ]

    def get_client_top_sites(self, hostname, limit=10):
        """
        Get top visited sites for a specific client hostname.

        Args:
            hostname: Client hostname to filter.
            limit: Maximum results.

        Returns:
            List of site info dictionaries.
        """
        results = (
            db.session.query(
                LogEntry.url,
                func.count(LogEntry.id).label("visit_count"),
            )
            .filter(
                LogEntry.client_hostname == hostname,
                LogEntry.log_type == "page_visit",
            )
            .group_by(LogEntry.url)
            .order_by(desc("visit_count"))
            .limit(limit)
            .all()
        )

        return [{"url": r[0], "count": r[1]} for r in results]


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
