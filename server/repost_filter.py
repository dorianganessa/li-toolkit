"""Filter reposts from post records. Expand later if needed."""

from database import PostRecord


def exclude_reposts(records: list[PostRecord]) -> list[PostRecord]:
    """Return only original posts (non-reposts)."""
    return [r for r in records if not r.is_repost]
