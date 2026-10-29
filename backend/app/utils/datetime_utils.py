"""
Timezone and DateTime normalization utilities.
Guarantees unambiguous UTC ISO 8601 representation (with 'Z') across all APIs and database interfaces,
while preserving calendar date-only strings (e.g. YYYY-MM-DD) without day-shifting.
"""

from datetime import datetime, timezone
from typing import Optional, Union
import dateutil.parser


def ensure_utc_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensures a datetime object is timezone-aware with UTC timezone.
    If the datetime is naive (as returned by SQLite DateTime columns), assigns UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_utc_iso(dt: Optional[Union[datetime, str]]) -> Optional[str]:
    """
    Serializes a datetime or ISO string to an unambiguous UTC ISO 8601 string ending with 'Z'.
    Preserves calendar-only date strings (e.g. '2026-10-28') as-is.
    
    Examples:
      datetime(2026, 10, 28, 17, 37, 0) -> '2026-10-28T17:37:00Z'
      '2026-10-28T17:37:00'             -> '2026-10-28T17:37:00Z'
      '2026-10-28'                      -> '2026-10-28'
    """
    if dt is None:
        return None

    if isinstance(dt, str):
        val = dt.strip()
        if not val:
            return None
        # Preserve date-only strings (YYYY-MM-DD)
        if len(val) == 10 and val[4] == '-' and val[7] == '-':
            return val
        if val.endswith('Z'):
            return val
        try:
            parsed = dateutil.parser.parse(val)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            else:
                parsed = parsed.astimezone(timezone.utc)
            return parsed.isoformat().replace("+00:00", "Z")
        except Exception:
            return val

    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    return str(dt)


def parse_utc_datetime(val: Union[datetime, str]) -> datetime:
    """
    Parses an ISO or standard datetime string / object into a timezone-aware UTC datetime.
    """
    if isinstance(val, datetime):
        return ensure_utc_datetime(val)
    
    try:
        dt = dateutil.parser.isoparse(val)
    except Exception:
        dt = dateutil.parser.parse(val)

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utc_now() -> datetime:
    """Returns current instant as timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)
