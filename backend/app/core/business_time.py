"""Business-day helpers.

Sellers think in local calendar days ("today", "this week"), so every range and
every daily/weekday/hourly bucket is computed in `settings.BUSINESS_TIMEZONE`,
never in UTC. Timestamps are still stored and compared in UTC.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import Date, Integer, cast, func

from app.config import settings

BUSINESS_TZ = ZoneInfo(settings.BUSINESS_TIMEZONE)

# Trailing local calendar days (including today) for each preset range.
RANGE_DAYS = {"today": 1, "week": 7, "month": 30}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def local_today() -> date:
    return now_utc().astimezone(BUSINESS_TZ).date()


def local_midnight_utc(day: date) -> datetime:
    """The UTC instant at which local `day` begins."""
    return datetime.combine(day, time.min, tzinfo=BUSINESS_TZ).astimezone(timezone.utc)


def day_bounds_utc(start: date, end: date) -> tuple[datetime, datetime]:
    """UTC `[start, end)` covering local days `start..end` inclusive."""
    return local_midnight_utc(start), local_midnight_utc(end + timedelta(days=1))


def _local_ts(col):
    # timestamptz AT TIME ZONE '<zone>' -> local wall-clock timestamp.
    return func.timezone(settings.BUSINESS_TIMEZONE, col)


def local_day_expr(col):
    return cast(_local_ts(col), Date)


def local_hour_expr(col):
    return cast(func.extract("hour", _local_ts(col)), Integer)


def local_weekday_expr(col):
    """Monday=0 … Sunday=6, matching `date.weekday()`."""
    return cast(func.extract("isodow", _local_ts(col)), Integer) - 1


@dataclass(frozen=True)
class DateRange:
    """Local calendar days `start..end`, both inclusive."""

    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    @property
    def start_utc(self) -> datetime:
        return local_midnight_utc(self.start)

    @property
    def end_utc(self) -> datetime:
        """Exclusive upper bound."""
        return local_midnight_utc(self.end + timedelta(days=1))

    def previous(self) -> "DateRange":
        """The equal-length window immediately before this one."""
        prev_end = self.start - timedelta(days=1)
        return DateRange(prev_end - timedelta(days=self.days - 1), prev_end)

    def each_day(self) -> list[date]:
        return [self.start + timedelta(days=i) for i in range(self.days)]


class InvalidRangeError(ValueError):
    pass


def resolve_range(range_key: str | None, start: date | None = None, end: date | None = None) -> DateRange:
    if range_key == "custom":
        if start is None or end is None:
            raise InvalidRangeError("start and end are required when range=custom")
        if start > end:
            raise InvalidRangeError("start must be on or before end")
        return DateRange(start, end)
    today = local_today()
    days = RANGE_DAYS.get(range_key or "week", 7)
    return DateRange(today - timedelta(days=days - 1), today)


def trailing_days(days: int) -> DateRange:
    """The last `days` local days, including today."""
    today = local_today()
    return DateRange(today - timedelta(days=days - 1), today)
