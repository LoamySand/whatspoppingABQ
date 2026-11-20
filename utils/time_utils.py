"""
App-wide clock helpers.

The pipeline runs in a UTC container, but every schedule, slot, event time and
stored timestamp in this app is Albuquerque local time. Read the clock through
these helpers instead of datetime.now() / date.today() / SQL CURRENT_DATE.

local_now() returns a naive datetime on purpose: traffic_measurements and
events use `timestamp without time zone`, and rows written before July 2026
are naive local time. Moving to timestamptz is a schema change (SCRUM-7).
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

APP_TZ = ZoneInfo("America/Denver")


def to_local(moment: datetime) -> datetime:
    """Convert a timezone-aware datetime to naive America/Denver time."""
    if moment.tzinfo is None:
        raise ValueError("to_local() needs a timezone-aware datetime")
    return moment.astimezone(APP_TZ).replace(tzinfo=None)


def local_now() -> datetime:
    """Current America/Denver time as a naive datetime."""
    return to_local(datetime.now(UTC))


def local_today() -> date:
    """Current America/Denver date."""
    return local_now().date()
