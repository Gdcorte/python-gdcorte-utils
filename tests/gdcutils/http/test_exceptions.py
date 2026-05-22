"""Exception testing."""

from fastapi import status

from gdcutils.http.exceptions import HttpBaseException, to_http_exc


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
