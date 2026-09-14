"""Date-related utility functions."""

from whenever import Instant, OffsetDateTime, PlainDateTime, ZonedDateTime

# Length of a string date as a naive string.
NAIVE_LEN = 19


def as_naive(date: str | Instant | ZonedDateTime) -> PlainDateTime:
    """Converts a string, or localized date to a naive date.

    This will effectively strip and ignore timezones.
    It means that there will be no offset when converting.

    Parameters
    ----------
    date
        Date to be stripped of timezone.

    Returns
    -------
        Timezone-stripped date.
    """
    if isinstance(date, str):
        return PlainDateTime(date[:NAIVE_LEN])

    if isinstance(date, Instant):
        return date.to_tz("UTC").to_plain()

    return date.to_plain()


def offset_to_naive_utc(date: str | Instant | ZonedDateTime) -> PlainDateTime:
    """Converts a string, or offset and convert a localized date to a naive date.

    This will, when applicable, offset the date to UTC and return a naive date.
    When no timezone is provided, just converts to naive date type.

    Parameters
    ----------
    date
        Date to be stripped of timezone.

    Returns
    -------
        Timezone-stripped date.
    """
    if isinstance(date, str):
        if len(date) <= NAIVE_LEN or date[-1] == "Z":
            return PlainDateTime(date[:NAIVE_LEN])

        # Need additional conversion to Instant first
        if date[-1] != "]":
            date = OffsetDateTime(date).to_instant()
        else:
            date = ZonedDateTime(date).to_instant()

    if isinstance(date, Instant):
        return date.to_tz("UTC").to_plain()

    return (date - date.offset).to_fixed_offset().to_plain()
