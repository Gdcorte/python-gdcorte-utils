"""Decorator utilities for HTTP routes.

This requires: FastAPI
"""

from collections.abc import AsyncIterable, Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from fastapi.responses import JSONResponse
from fastapi.sse import ServerSentEvent

from gdcutils.http.exceptions import HttpBaseException, to_http_exc
from gdcutils.http.logging import get_logger

P = ParamSpec("P")
R = TypeVar("R")


def process_exception(exc: BaseException, name: str) -> HttpBaseException:
    """Log the exception here and convert it to HttpBase.

    The idea here is that all converted exceptions will be automatically logged here.

    Parameters
    ----------
    exc
        Exception to be processed
    name
        Which route raised it.

    Returns
    -------
        Converted exception, ready to give out standardized messages
    """
    treat_exc = to_http_exc(exc=exc)

    logger = get_logger()

    # We can have critical errors, provenient from the server (5xx).
    # Those must be addressed immediately.
    if treat_exc.err.status >= 500:
        logger.critical("Server error on route %s", name, exc_info=True)

    # Or we can have some client-side issues (4xx), such as an user trying to access what it
    # does not have permission. Those should be logged, but are not so alarming at first.
    # We must do some investigation, and/or client education to prevent system abuse.
    else:
        logger.warning("Client abnormality on route %s", name, exc_info=True)

    # debug of info should never come down here. They are mostly local...
    return treat_exc


def treat_http_errors(
    func: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R | JSONResponse]]:
    """Error treatment for FastAPI HTTP routes.

    This decorator will catch all the errors raised inside your FastAPI application.


    NOTE: This applies to all errors encountered AFTER FastAPI finishes parsing the request
    body/contents. If an error is raised before that, this decorator does not cover it.
    One such error is RequestValidationError.

    For that, please refer to the exception treatment function directly.

    Please attach it directly to your FastAPI application by leveraging FastAPI app.add_exception_handler,
    or using their decorated registration method:
    [@app.exception_handler](https://fastapi.tiangolo.com/tutorial/handling-errors/#override-request-validation-exceptions)
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | JSONResponse:

        try:
            return await func(*args, **kwargs)

        # The idea here is to catch all exceptions to treat them accordingly.
        # This should be applied to the root of your HTTP route with FastAPI,
        # meaning everything gets funneled here and no weird messages to requesters get out.
        # pylint: disable=broad-exception-caught
        except BaseException as exc:
            treat_exc = process_exception(exc=exc, name=func.__name__)
            return treat_exc.model_dump_response(mode=JSONResponse)

    return wrapper


def treat_stream_errors(
    func: Callable[P, AsyncIterable[str | ServerSentEvent]],
) -> Callable[P, AsyncIterable[ServerSentEvent]]:
    """Error treatment for FastAPI HTTP routes.

    This decorator will catch all the errors raised inside your FastAPI application.


    NOTE: This applies to all errors encountered AFTER FastAPI finishes parsing the request
    body/contents. If an error is raised before that, this decorator does not cover it.
    One such error is RequestValidationError.

    For that, Please attach it directly to your FastAPI application by leveraging FastAPI decorated registration method:
    [@app.exception_handler](https://fastapi.tiangolo.com/tutorial/handling-errors/#override-request-validation-exceptions)
    The custom method is not provided here, as it will be a very simple wrapper around the execption using `process_exception`
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> AsyncIterable[ServerSentEvent]:

        try:
            async for item in func(*args, **kwargs):
                if isinstance(item, ServerSentEvent):
                    yield item
                else:
                    yield ServerSentEvent(data=item)

        # The idea here is to catch all exceptions to treat them accordingly.
        # This should be applied to the root of your HTTP route with FastAPI,
        # meaning everything gets funneled here and no weird messages to requesters get out.
        # pylint: disable=broad-exception-caught
        except BaseException as exc:
            treat_exc = process_exception(exc=exc, name=func.__name__)
            yield treat_exc.model_dump_response(mode=ServerSentEvent)

        finally:
            yield ServerSentEvent(event="done", raw_data="[DONE]")

    return wrapper
