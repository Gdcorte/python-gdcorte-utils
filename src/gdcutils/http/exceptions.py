"""Exception utils."""

import json
from typing import Any, TypedDict, Unpack, overload

from fastapi import status as http_status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.sse import ServerSentEvent
from pydantic import BaseModel, ConfigDict


class _ErrCtx(BaseModel):
    """Error context structured model."""

    model_config = ConfigDict(extra="allow")

    user: str | None = None
    trace: str | None = None
    endpoint: str | None = None


class _ErrDetails(BaseModel):
    """Error details structured model."""

    model_config = ConfigDict(extra="allow")

    cause: str | None = None


class Error(BaseModel):
    """Summarized error for application i18n."""

    model_config = ConfigDict(extra="ignore")

    status: int
    code: str
    group: str

    def model_dump_summary(self) -> dict[str, Any]:
        """Builds a JSONable dict to output the user request.

        This is being used here to make sure only the fields in this model
        go out from the API response in case of error.

        This makes sure the logs get all the traceback and execution information, while
        the application calling the API receives only what it needs to display messages to users
        or reach out to support.

        The codes pairing in code,group allow for easy i18n for frontent apps.
        Returns
        -------
            A nice error summary with the error details.
        """
        fields = set(Error.model_fields.keys())

        return self.model_dump(mode="json", include=fields)


class FullError(Error):
    """Standard error structured model (for logging/serialization)."""

    log: str | None = None
    details: _ErrDetails | None = None
    ctx: _ErrCtx | None = None


class ErrorResponse(BaseModel):
    """Standard Error response for HTTP endpoints."""

    msg: str
    error: Error


class ErrCtxDict(TypedDict, total=False):
    """Public error context structure."""

    user: str
    trace: str
    endpoint: str


class HttpBaseExcKwargs(TypedDict, total=False):
    """Unpackable kwargs."""

    log_msg: str
    user_msg: str | None
    status: int
    err_code: str
    err_group: str
    err_details: dict[str, Any] | None
    err_ctx: ErrCtxDict | None


class HttpBaseException(Exception):
    """Root level exception fine-tuned for HTTP responses."""

    err: FullError
    msg: str

    def __init__(
        self,
        *,
        log_msg: str | None = None,
        user_msg: str | None = None,
        status: int = http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        err_code: str = "unknown_server_error",
        err_group: str = "unknown_error",
        err_details: dict[str, Any] | None = None,
        err_ctx: ErrCtxDict | None = None,
    ) -> None:
        self.msg = user_msg or "An unknown error happened, please try again later."

        self.err = FullError(
            log=log_msg,
            status=status,
            code=err_code,
            group=err_group,
            details=_ErrDetails.model_validate(err_details) if err_details else None,
            ctx=_ErrCtx.model_validate(err_ctx) if err_ctx else None,
        )

        super().__init__(log_msg)

    @overload
    def model_dump_response(self, mode: type[ServerSentEvent]) -> ServerSentEvent: ...

    @overload
    def model_dump_response(self, mode: type[JSONResponse]) -> JSONResponse: ...

    @overload
    def model_dump_response(self, mode: None = None) -> dict[str, Any]: ...

    def model_dump_response(
        self,
        mode: type[ServerSentEvent] | type[JSONResponse] | None = None,
    ) -> ServerSentEvent | JSONResponse | dict[str, Any]:
        """Dumps the error in an API friendly way.

        It will strip out the details and print a message with a targeted message with what went wrong and a nice summary of the error itself, preserving the
        HTTP status code associated to the error as best as it can.

        Parameters
        ----------
        mode, optional
            Reponse mode to accomodate different natures of the API

        Returns
        -------
            The error, coerced to the specified type
        """
        err_summary: dict[str, Any] = {
            "msg": self.msg,
            "err": self.err.model_dump_summary(),
        }

        if mode is JSONResponse:
            return JSONResponse(
                status_code=self.err.status,
                content=err_summary,
            )

        if mode is ServerSentEvent:
            return ServerSentEvent(
                event="error",
                data=json.dumps(err_summary),
            )

        return err_summary


def to_http_exc(exc: BaseException, **kwargs: Unpack[HttpBaseExcKwargs]) -> HttpBaseException:
    """Converts a generic exception to an HttpBaseException.

    Parameters
    ----------
    exc
        Generic exception object

    Returns
    -------
        Structured HttpBaseException
    """
    if isinstance(exc, HttpBaseException):
        return exc

    status_code: int = http_status.HTTP_500_INTERNAL_SERVER_ERROR
    # This is, undoubtedly, a 400 and should not be coerced into a server error.
    if isinstance(exc, RequestValidationError):
        status_code = http_status.HTTP_400_BAD_REQUEST
    kwargs.setdefault("status", status_code)

    # Try to preserve the original details from the parent exception.
    err_details = kwargs.get("err_details", {})
    if err_details is not None:
        err_details["cause"] = str(exc)

    kwargs["err_details"] = err_details
    kwargs.setdefault("log_msg", str(exc))

    http_exc = HttpBaseException(**kwargs)
    http_exc.__cause__ = exc  # Manual linking

    return http_exc
