"""Exception utils."""

from typing import Any, TypedDict, Unpack

from fastapi import status as http_status
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

    status: int
    code: str
    group: str


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

    # Try to preserve the original details from the parent exception.
    err_details = kwargs.get("err_details", {})
    if err_details is not None:
        err_details["cause"] = str(exc)

    kwargs["err_details"] = err_details
    kwargs.setdefault("log_msg", str(exc))

    http_exc = HttpBaseException(**kwargs)
    http_exc.__cause__ = exc  # Manual linking

    return http_exc
