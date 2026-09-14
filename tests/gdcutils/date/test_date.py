"""Date module testing."""

import pytest
from whenever import Instant, ZonedDateTime

from gdcutils import date


@pytest.mark.parametrize(
    "input_date",
    [
        "2024-07-04T00:36:56Z",
        "2024-07-04 00:36:56",
        "2024-07-04 23:36:56-03:00",
        "2024-07-04T00:36:56+02:00",
        "2024-07-04 00:36:56+08:00[Europe/Paris]",
        Instant("2024-07-04 00:36:56Z"),
        ZonedDateTime("2024-07-04 00:36:56+02:00[Europe/Paris]"),
    ],
)
async def test_tz_stripping_conversion_works(input_date: str | Instant | ZonedDateTime) -> None:
    """Test that stripping the TZ-date to naive works as expected."""
    converted = date.as_naive(input_date)

    assert converted.day == 4
    assert converted.month == 7
    assert converted.year == 2024


@pytest.mark.parametrize(
    "input_date",
    [
        "2024-07-04T00:36:56Z",
        "2024-07-03 23:36:56-03:00",
        "2024-07-05T00:36:56+02:00",
        "2024-07-05 00:36:56+09:00[Asia/Tokyo]",
        Instant("2024-07-04 00:36:56Z"),
        ZonedDateTime("2024-07-05 00:36:56+02:00[Europe/Paris]"),
    ],
)
async def test_tz_offsetting_conversion_works(input_date: str | Instant | ZonedDateTime) -> None:
    """Test that offsetting the TZ-date to naive works as expected."""
    converted = date.offset_to_naive_utc(input_date)

    assert converted.day == 4
    assert converted.month == 7
    assert converted.year == 2024
