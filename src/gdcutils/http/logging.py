"""Logging utils."""

import json
import logging
import traceback
from typing import Any, TypedDict

from pydantic_settings import BaseSettings, SettingsConfigDict
from whenever import Instant

from gdcutils.http.exceptions import to_http_exc


class LogSettings(BaseSettings):
    """Log customizeable settings."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="LOGGING_",
    )

    level: int = logging.WARNING


class BaseLogMessage(TypedDict):
    """Base message common to all levels."""

    timestamp: str
    level: str
    message: str
    module: str
    function: str
    line: int


class ErrData(TypedDict):
    """Error data object"""

    type: str
    stack: str
    data: dict[str, Any]


class ErrLogMessage(BaseLogMessage):
    """Error level messages that should contain all error traceback"""

    user_msg: str
    err: ErrData


class JsonFormatter(logging.Formatter):
    """Logging JSON formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: BaseLogMessage = {
            "timestamp": Instant.now().format_iso(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        exc = record.exc_info
        if exc:
            exc_type, exc_value, exc_tb = exc
            if exc_value is None or exc_type is None:
                return json.dumps(log_data)

            stack_trace: str = ""
            if exc_tb:
                stack_trace = "".join(
                    traceback.format_exception(
                        exc_type,
                        exc_value,
                        exc_tb,
                    )
                )

            # Just a small supercharging here.
            exc_value = to_http_exc(exc=exc_value)

            err_data: ErrLogMessage = {
                **log_data,
                "user_msg": exc_value.msg,
                "err": ErrData(
                    stack=stack_trace,
                    data=exc_value.err.model_dump(mode="json"),
                    type=exc_type.__name__,
                ),
            }
            return json.dumps(err_data)

        return json.dumps(log_data)


def get_logger(name: str | None = "app_logger") -> logging.Logger:
    """Get the customized logging handler.

    Parameters
    ----------
    name, optional
        name for the log stream.

    Returns
    -------
        the logger to enable logging.
    """
    settings = LogSettings()

    logger = logging.getLogger(name)
    logger.setLevel(settings.level)

    if name is not None:
        logger.propagate = False

    if logger.handlers:
        return logger

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger
