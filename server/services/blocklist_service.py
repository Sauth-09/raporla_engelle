"""
Blocklist service implementation.
Handles blacklist and whitelist CRUD operations and provides
combined data formatted for the Chrome extension.
"""

from server.models.base import db
from server.models.blocked_item import BlockedItem
from server.models.whitelisted_item import WhitelistedItem
from server.services.interfaces import IBlocklistService


class BlocklistService(IBlocklistService):
    """Concrete implementation of blacklist/whitelist management."""

    # ── Blacklist Operations ──────────────────────────────────────────

    def get_blocked_items(self, active_only=True):
        """Get all blocked items, optionally filtered by active status."""
        query = BlockedItem.query
        if active_only:
            query = query.filter(BlockedItem.is_active.is_(True))
        return query.order_by(BlockedItem.created_at.desc()).all()

    def add_blocked_item(self, pattern, block_type, is_regex=False, description=None):
        """
        Add a new item to the blacklist.

        Args:
            pattern: The blocking pattern (keyword, URL, channel ID, etc.)
            block_type: Type of block (keyword, url, channel_id, channel_name, video_id, regex)
            is_regex: Whether the pattern is a regular expression.
            description: Optional human-readable description.

        Returns:
            The created BlockedItem.
        """
        item = BlockedItem(
            pattern=pattern.strip(),
            block_type=block_type,
            is_regex=is_regex,
            description=description,
        )
        db.session.add(item)
        db.session.commit()
        return item

    def remove_blocked_item(self, item_id):
        """Remove an item from the blacklist by ID."""
        item = db.session.get(BlockedItem, item_id)
        if item:
            db.session.delete(item)
            db.session.commit()
            return True
        return False

    def toggle_blocked_item(self, item_id):
        """Toggle the active status of a blocked item."""
        item = db.session.get(BlockedItem, item_id)
        if item:
            item.is_active = not item.is_active
            db.session.commit()
            return item
        return None

    # ── Whitelist Operations ──────────────────────────────────────────

    def get_whitelisted_items(self, active_only=True):
        """Get all whitelisted items, optionally filtered by active status."""
        query = WhitelistedItem.query
        if active_only:
            query = query.filter(WhitelistedItem.is_active.is_(True))
        return query.order_by(WhitelistedItem.created_at.desc()).all()

    def add_whitelisted_item(self, pattern, whitelist_type, description=None):
        """
        Add a new item to the whitelist.

        Args:
            pattern: The whitelisting pattern.
            whitelist_type: Type (channel_id, channel_name, url, keyword).
            description: Optional description.

        Returns:
            The created WhitelistedItem.
        """
        item = WhitelistedItem(
            pattern=pattern.strip(),
            whitelist_type=whitelist_type,
            description=description,
        )
        db.session.add(item)
        db.session.commit()
        return item

    def remove_whitelisted_item(self, item_id):
        """Remove an item from the whitelist by ID."""
        item = db.session.get(WhitelistedItem, item_id)
        if item:
            db.session.delete(item)
            db.session.commit()
            return True
        return False

    def toggle_whitelisted_item(self, item_id):
        """Toggle the active status of a whitelisted item."""
        item = db.session.get(WhitelistedItem, item_id)
        if item:
            item.is_active = not item.is_active
            db.session.commit()
            return item
        return None

    # ── Extension Data ────────────────────────────────────────────────

    def get_blocklist_for_extension(self):
        """
        Get combined blocklist data formatted for the Chrome extension.
        Groups items by their block type for efficient client-side filtering.

        Returns:
            Dictionary with categorized block/whitelist patterns.
        """
        blocked = self.get_blocked_items(active_only=True)
        whitelisted = self.get_whitelisted_items(active_only=True)

        blocklist = _group_items_by_type(
            blocked, type_attr="block_type", pattern_attr="pattern", regex_attr="is_regex"
        )
        whitelist = _group_items_by_type(
            whitelisted, type_attr="whitelist_type", pattern_attr="pattern"
        )

        return {
            "blocklist": blocklist,
            "whitelist": whitelist,
        }


def _group_items_by_type(items, type_attr, pattern_attr, regex_attr=None):
    """
    Group list items by their type attribute.

    Returns:
        Dictionary mapping type names to lists of pattern strings.
    """
    grouped = {}
    for item in items:
        item_type = getattr(item, type_attr)
        pattern = getattr(item, pattern_attr)

        if item_type not in grouped:
            grouped[item_type] = []

        entry = {"pattern": pattern}
        if regex_attr and getattr(item, regex_attr, False):
            entry["is_regex"] = True

        grouped[item_type].append(entry)

    return grouped
