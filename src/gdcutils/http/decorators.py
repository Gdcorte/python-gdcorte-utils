"""Decorator utilities for HTTP routes.

This requires: FastAPI
"""

from collections.abc import AsyncIterable, Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

from fastapi import status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.sse import ServerSentEvent
from httpx import URL
from pydantic import BaseModel, ConfigDict, model_validator

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

    NOTE: This is NOT fit for Redirect routes. That is a beast of their own league.
    Please look at treat_redirect_errors to slay those beats.

    NOTE: This applies to all errors encountered AFTER FastAPI finishes parsing the request
    body/contents. If an error is raised before that, this decorator does not cover it.
    One such error is RequestValidationError.

    For that, please refer to the exception treatment function directly.

    Please attach it directly to your FastAPI application by leveraging FastAPI app.exception_handler, their decorated registration method:
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
    """Error treatment for FastAPI Streaming routes.

    This decorator will catch all the errors raised inside your FastAPI application.

    NOTE: For RequestValidationErrors, pleasse see `treat_http_errors`.
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


class RedirectCtx(BaseModel):
    """
    Context with minimally required information to provide a consistent redirect.

    Oauth2 fields are here for compatibility on errors. But they are all optional here.
    Plase use a better model if you intend to use Oauth2.1 in your workflow.
    But please extend this method in your applicaiton to provide a better interface.
    """

    model_config = ConfigDict(extra="ignore")

    # Oauth 2.1 fields
    state: str | None = None
    scope: list[str] | None = None
    redirect_uri: str | None = None
    response_type: str | None = None
    client_id: str | None = None
    code_challenge: str | None = None
    code_challenge_method: str | None = None


class ErrorRedirectCtx(BaseModel):
    """Minimally required"""

    model_config = ConfigDict(extra="ignore")

    origin: str
    path: str | None = None
    query: RedirectCtx | None = None

    @model_validator(mode="before")
    @classmethod
    def allow_flat_params(cls, data: Any) -> Any:
        """Allow for raw data to be a flat dictionary.

        Ideally, routes will have a variable to absorb query parameters.
        But in its absence, you can also capture all paramters as a flat dictionary
        and build a new model instance.

        Parameters
        ----------
        data
            Input that that will replicate its contents onto a query field for
            model building.

        Returns
        -------
            The model instance.
        """
        if isinstance(data, dict):
            # If by any chance, the query parameters are not bundled
            # in a single query object in the route definition
            if "query" not in data:
                data["query"] = data.copy()

        # Need to have this here for liner's sake, but here we
        # should always have a dictionary
        return cast(Any, data)

    def model_dump_url(self) -> URL:
        """Dumps model into a httpx.URL object

        Returns
        -------
            Serialized model fields onto a httpx.URL structure
        """
        # TODO: docstrings
        url_params = self.query.model_dump(exclude_none=True) if self.query else None

        return URL(
            url=self.origin,
            path=self.path,
            params=url_params,
        )


def treat_redirect_errors(
    func: Callable[P, Awaitable[RedirectResponse]],
) -> Callable[P, Awaitable[RedirectResponse]]:
    """Error treatment for FastAPI redirect routes.

    This decorator will catch all the errors raised inside your FastAPI application.

    A few premises are made here. Because we have no control over all the exceptions in
    the system and also cannot guarantee that all exceptions originating in the code are
    tailored to suit those kind of endpoints, routes that use this must declare, in their
    function signature, a few variables.
    Those variables are there to ensure that, even in case of an error, we can redirect
    the request BACK to the sender, with the appropriate URL.
    - origin:
        - Location: Header
        - Format: string
        - It is usually present in the request header of all HTTP request sent from the
        browser (frontend, overwhelming majority of cases).
        You can easily inject into the function signature with FastAPI Depends and Header
        helpers. It will add as a `base_url` to be redirected to. You should let the
        request fail catastrophically if this is not passed somehow... For security reasons, this must be a domain, without any paths (From the browser, this will be
        automatically done for you).
    - path:
        - Location: Query string
        - Format: encoded string
        - This is a custom, arbitrarily named variable. You can define a default value in
        case this is not passed by the client. But the client should be able to specify
        this during request time. For secutiry reasons, this must be a properly encoded
        string. Upon decoding, this must be a traditional url path, without the domain, that will be appended to the origin. If omitted, assumes no path



    NOTE: For RequestValidationErrors, pleasse see `treat_http_errors`.
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> RedirectResponse:

        try:
            return await func(*args, **kwargs)

        except Exception as exc:  # pylint: disable=broad-exception-caught
            ctx = ErrorRedirectCtx.model_validate(kwargs)
            url = ctx.model_dump_url()

            treat_exc = process_exception(exc=exc, name=func.__name__)

            return_status = treat_exc.err.status
            if return_status < 300 or return_status >= 400:
                return_status = status.HTTP_307_TEMPORARY_REDIRECT

            # Add error to url
            err_sum = treat_exc.model_dump_response(mode=None)
            url = url.copy_add_param(key="err", value=err_sum)

            return RedirectResponse(
                url=str(url),
                status_code=return_status,
            )

    return wrapper
