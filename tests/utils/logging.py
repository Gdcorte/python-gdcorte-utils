"""logging utilities"""

import io
import logging
from collections.abc import Generator
from contextlib import contextmanager


@contextmanager
def buffered_logger_setup(
    name: str = "test_log",
    formatter: logging.Formatter | None = None,
) -> Generator[tuple[logging.Logger, io.StringIO]]:
    """Utility function to yield a log that writes to buffer.

    This allow for log testing setup

    Parameters
    ----------
    name, optional
        name of the logger.
    formatter, optional
        custom formatter to be applied

    Yields
    ------
        A logger and a buffer. The logs will be written to the buffer
        and can be recovered by the testing method.
    """
    logger = logging.getLogger(name)

    # Set logger to send to buffer
    buffer = io.StringIO()
    test_handler = logging.StreamHandler(buffer)
    test_handler.setFormatter(formatter)
    logger.addHandler(test_handler)

    yield (logger, buffer)
