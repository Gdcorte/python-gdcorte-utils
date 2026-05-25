"""Exception testing."""

import json
from typing import Any, cast

import pytest
from fastapi import status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.sse import ServerSentEvent

from gdcutils.http.exceptions import FullError, HttpBaseException, to_http_exc


def test_base_exception_raises_server_error() -> None:
    """Test unknown server error with 500 status code is raised automatically."""

    new_exc = HttpBaseException()
    assert new_exc.err.status == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert all(sub in new_exc.err.group for sub in ["unknown", "error"])
    assert all(sub in new_exc.err.code for sub in ["unknown", "server", "error"])


def test_exc_conversion_preserves_messages() -> None:
    """Test converting exceptions to the HTTP base standard will preserve their original message."""
    original_msg = "oops"

    original_exc = Exception(original_msg)

    custom = to_http_exc(original_exc, err_details={"why": "not on my watch!"})

    assert custom.err.details
    assert custom.err.details.cause
    assert original_msg in custom.err.details.cause


def test_full_error_generates_summary() -> None:
    """Test an Error Summary can be generated from a full error."""

    full_err = FullError.model_validate(
        {
            "status": 600,
            "code": "not_an_error",
            "group": "testing_errors",
            "log": "not on my watch",
            "details": {
                "cause": "not cause",
            },
            "ctx": {"user": "uid"},
        }
    )

    summary = full_err.model_dump_summary()
    assert summary.get("details") is None
    assert summary.get("log") is None
    assert summary.get("ctx") is None


def test_req_validation_err_is_400() -> None:
    """Test FastAPI RequestValidationError coerces to a bad request."""

    exc = RequestValidationError(errors=[])

    treated_exc = to_http_exc(exc=exc)
    assert treated_exc.err.status == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize(
    "resp_type",
    [
        JSONResponse,
        ServerSentEvent,
        None,
    ],
)
def test_exc_can_generate_http_response(
    resp_type: type[ServerSentEvent] | type[JSONResponse] | None,
) -> None:
    """Test all supported conversion methods yield good responses."""
    expected_msg = "MY USER!"

    raw_exc = HttpBaseException(user_msg=expected_msg)

    nice_response = raw_exc.model_dump_response(mode=resp_type)

    # Because the parametrize, doing some juggling here
    if resp_type is JSONResponse:
        nice_response = cast(JSONResponse, nice_response)
        resp_msg = cast(bytes, nice_response.body)
        assert json.loads(resp_msg.decode())["msg"] == expected_msg

    if resp_type is ServerSentEvent:
        nice_response = cast(ServerSentEvent, nice_response)
        assert nice_response.data
        assert not nice_response.raw_data
        assert json.loads(nice_response.data)["msg"] == expected_msg

    if resp_type is None:
        nice_response = cast(dict[str, Any], nice_response)
        assert nice_response["msg"] == expected_msg
