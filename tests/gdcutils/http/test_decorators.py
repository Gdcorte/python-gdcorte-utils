"""FastAPI Route decorators testing."""

from collections.abc import AsyncIterable
from typing import Any
from urllib.parse import quote_plus

from fastapi import FastAPI, status
from fastapi.responses import RedirectResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.testclient import TestClient

from gdcutils.http.decorators import RedirectCtx, treat_http_errors, treat_redirect_errors, treat_stream_errors
from gdcutils.http.exceptions import HttpBaseException


async def test_http_decorator_works_as_expected() -> None:
    """Test HTTP routes will not leak the exception to outside the route."""
    expected_msg = "öhh la la"
    expected_status = status.HTTP_404_NOT_FOUND
    app = FastAPI()

    @app.get("/")
    @treat_http_errors
    async def my_root() -> Any:  # pyright: ignore[reportUnusedFunction]
        """Testing function"""

        # This will force a 4xx
        raise HttpBaseException(status=expected_status, user_msg=expected_msg)

    client = TestClient(app=app)
    response = client.get(url="/")

    body = response.json()
    assert body["msg"] == expected_msg
    assert body["err"]["status"] == expected_status


async def test_stream_decorator_works_as_expected() -> None:
    """Test streaming endpoints will not leak exception outside the route."""
    expected_msg = "öhh la la"
    expected_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    app = FastAPI()

    @app.post("/", response_class=EventSourceResponse)
    @treat_stream_errors
    async def my_root() -> AsyncIterable[str | ServerSentEvent]:  # pyright: ignore[reportUnusedFunction]
        """Testing function"""
        # this should result in a standard data server sent event
        yield "hello"

        # this should be preserved by the decorator
        yield ServerSentEvent(event="custom", data="another custom")

        # This will end the transmission, but will send one last event with the error before
        # gracefully stopping
        raise HttpBaseException(status=expected_status, user_msg=expected_msg)

    client = TestClient(app=app)
    with client.stream("POST", "/") as response:
        assert response.status_code

        # All the responses, down to the exception event, will be clotted
        # because of how the stream testing works for FastAPI. the testing  endpoint
        # is no real streaming. But it will behave like a streming in prod.
        full_response = response.read().decode().split("\n\n")

        assert full_response[0].startswith("data: ")
        assert full_response[1].startswith("event: custom")
        assert full_response[2].startswith("event: error")


async def test_redirect_decorator_works_as_expected() -> None:
    """Test redirect endpoints will not leak exception outside the route."""
    err_status = status.HTTP_410_GONE
    my_origin = "https://my.origin.gin"
    my_path = "/a/b/c/d"
    app = FastAPI()

    @app.get("/", response_class=RedirectResponse)
    @treat_redirect_errors
    async def my_redirect_root(  # pyright: ignore[reportUnusedFunction]
        origin: str = my_origin,
        path: str = my_path,
    ) -> RedirectResponse:
        """Testing function"""

        # This will end the transmission, but will send one last event with the error before
        # gracefully stopping
        raise HttpBaseException(status=err_status, user_msg="oh la la")

    client = TestClient(app=app)
    response = client.get("/", follow_redirects=False)

    location: str | None = response.headers.get("location")
    assert response.status_code < 400

    assert location
    assert "client_id" not in location
    assert "code_challenge" not in location
    assert "code_challenge_method" not in location
    assert "err" in location
    assert my_path in location
    assert my_origin in location
    assert str(err_status) in location


async def test_redirect_decorator_preserve_query_on_error() -> None:
    """Test redirect endpoints will not discard Oauth2.1 query parameters."""
    err_status = status.HTTP_425_TOO_EARLY
    my_origin = "https://my.origin.gin"
    app = FastAPI()

    query = RedirectCtx(
        client_id="Blanka",
        code_challenge="HERE COMES A NEW CHALLENGER",
        code_challenge_method="Pressed Start",
    )

    @app.get("/", response_class=RedirectResponse)
    @treat_redirect_errors
    async def my_redirect_root(  # pyright: ignore[reportUnusedFunction]
        origin: str = my_origin,
        query: dict[str, Any] = query.model_dump(),
    ) -> RedirectResponse:
        """Testing function"""

        # This will end the transmission, but will send one last event with the error before
        # gracefully stopping
        raise HttpBaseException(status=err_status, user_msg="oh la la")

    client = TestClient(app=app)
    response = client.get("/", follow_redirects=False)

    location: str | None = response.headers.get("location")
    assert response.status_code < 400

    assert location

    assert query.client_id
    assert query.client_id in location

    assert query.code_challenge
    assert quote_plus(query.code_challenge) in location

    assert query.code_challenge_method
    assert quote_plus(query.code_challenge_method) in location
