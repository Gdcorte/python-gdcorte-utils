"""Logs testing."""

import json
import logging

import pytest
from fastapi import status
from pytest_mock import MockerFixture

from gdcutils.http.exceptions import HttpBaseException
from gdcutils.http.logging import BaseLogMessage, ErrLogMessage, JsonFormatter, get_logger
from tests.utils import buffered_logger_setup


def test_log_formatting() -> None:
    """Test Log formatting incorporates all desired data."""
    test_exc = HttpBaseException()

    with buffered_logger_setup(formatter=JsonFormatter()) as (logger, buffer):
        try:
            raise test_exc
        except HttpBaseException:
            logger.error("hello darkness", exc_info=True)

        raw_output = buffer.getvalue()
        log_record: ErrLogMessage = json.loads(raw_output.strip())
        assert log_record["timestamp"]
        assert log_record["err"]
        assert log_record["err"]["stack"]
        assert log_record["err"]["type"] == HttpBaseException.__name__


def test_log_non_base_is_converted_to_base() -> None:
    """Test that non HttpBaseException are converted.

    When the log converts, the base exception is reflected only in the error data.
    """

    with buffered_logger_setup(formatter=JsonFormatter()) as (logger, buffer):
        try:
            raise ValueError("hello motto")
        except ValueError:
            logger.error("hello darkness", exc_info=True)

        raw_output = buffer.getvalue()
        log_record: ErrLogMessage = json.loads(raw_output.strip())
        assert log_record["timestamp"]
        assert log_record["err"]
        assert log_record["err"]["stack"]
        assert log_record["err"]["type"] == ValueError.__name__
        assert log_record["err"]["data"]["status"] == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_log_error_is_not_sent_for_malformed_exc() -> None:
    """Test that malformed exceptions do not translate to error message

    When the log converts, the base exception is reflected only in the error data.
    """

    with buffered_logger_setup(formatter=JsonFormatter()) as (logger, buffer):
        try:
            raise ValueError("hello motto")
        except ValueError:
            logger.error("hello darkness", exc_info=(None, None, None))

        raw_output = buffer.getvalue()
        log_record: BaseLogMessage = json.loads(raw_output.strip())
        assert log_record["timestamp"]
        assert not hasattr(log_record, "err")


@pytest.mark.parametrize(
    "loglevel",
    [
        logging.INFO,
        logging.DEBUG,
    ],
)
def test_log_debug_info_will_not_trigger_error(
    loglevel: int,
) -> None:
    """Test that debug and info logs will not show the full error, just base message."""

    with buffered_logger_setup(formatter=JsonFormatter()) as (logger, buffer):
        logger.setLevel(loglevel)

        try:
            raise ValueError("hello motto")
        except ValueError:
            if loglevel == logging.DEBUG:
                logger.debug("hello debugging")

            if loglevel == logging.INFO:
                logger.info("hello info")

        raw_output = buffer.getvalue()
        log_record: BaseLogMessage = json.loads(raw_output.strip())
        assert log_record["timestamp"]
        assert not hasattr(log_record, "err")


def test_logger_will_not_propagate_to_root() -> None:
    """Test logger propagate is False for named logs."""

    logger = get_logger(name="my_test")

    assert not logger.propagate


def test_multiple_calls_will_not_add_multiple_handlers(
    mocker: MockerFixture,
) -> None:
    """Test a handler is attached only once to the same named logger."""
    handler = mocker.patch("src.gdcutils.http.logging.logging.StreamHandler")

    # Pytest actually keeps the previously created logs...
    # To ensure a heuristic test for this scenario,
    # this here needs to be unique
    get_logger(name="my_multiple_test")
    get_logger(name="my_multiple_test")

    assert handler.call_count == 1


def test_root_will_receive_handler() -> None:
    """Assert root logs get the JsonFormatter"""
    logger = get_logger()

    assert isinstance(logger.handlers[0].formatter, JsonFormatter)
