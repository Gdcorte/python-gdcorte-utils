"""Test pool-based database manipulation."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import psycopg
import pytest
from fastapi import FastAPI
from pydantic import BaseModel
from pytest_mock import MockerFixture

from gdcutils.db.postgres import pg_conn, pg_fastapi_lifespan, pg_pool_lifespan
from gdcutils.db.postgres.exceptions import PgConstraintViolation
from gdcutils.db.postgres.interfaces.pool import PgPoolProvider
from gdcutils.db.postgres.service import pg_cursor


class MockConn(AsyncMock):
    """Fake Con Manager."""

    factory_type: str | None

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self.factory_type = None

    # pylint: disable=unused-argument
    @asynccontextmanager
    async def cursor(
        self,
        *args: Any,
        row_factory: Any,
        **kwargs: Any,
    ) -> AsyncGenerator[MagicMock]:
        """fake cursor."""
        self.factory_type = row_factory.__name__

        yield MagicMock()


class MockAsyncPool(AsyncMock):
    """Fake conn pool"""

    closed: bool
    conn_count: int
    connect: MockConn

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self.connect = MockConn()
        self.conn_count = 0

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[MockConn]:
        """Fake Connection"""
        self.conn_count += 1
        yield self.connect

    async def open(self) -> None:
        """Faks Open"""
        self.closed = False

    async def close(self) -> None:
        """Fake Close"""
        self.closed = True


async def test_unit_it_can_connect_using_pool_with_db(
    mocker: MockerFixture,
) -> None:
    """Test it can connect to PostgreSQL using a specific database."""
    pool = mocker.patch(
        "gdcutils.db.postgres.interfaces.pool.AsyncConnectionPool",
        return_value=MockAsyncPool(),
    )

    async with pg_fastapi_lifespan(app=FastAPI()):
        async with pg_conn():
            assert pool.call_count == 1


async def test_unit_it_can_connect_using_pool_with_no_db(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
) -> None:
    """Test it can connect to PostgreSQL without a specific database."""
    monkeypatch.delenv("PG_DB")

    pool = mocker.patch(
        "gdcutils.db.postgres.interfaces.pool.AsyncConnectionPool",
        return_value=MockAsyncPool(),
    )

    async with pg_pool_lifespan():
        async with pg_conn():
            assert pool.call_count == 1


async def test_unit_it_can_get_cursor_without_passing_conn(
    mocker: MockerFixture,
) -> None:
    """Test a cursor can be acquired directly."""
    pool = mocker.patch(
        "gdcutils.db.postgres.interfaces.pool.AsyncConnectionPool",
        return_value=MockAsyncPool(),
    )

    async with pg_fastapi_lifespan(app=FastAPI()):
        async with pg_cursor():
            assert pool.call_count == 1


async def test_unit_it_can_close_without_client(
    mocker: MockerFixture,
) -> None:
    """Test a pool can be safely closed even if no client is initialized."""
    mocker.patch("gdcutils.db.postgres.interfaces.pool.AsyncConnectionPool")

    # Reset Singleton
    # pylint: disable=protected-access
    PgPoolProvider._instances = {}  # pyright: ignore[reportPrivateUsage]

    provider = PgPoolProvider()
    await provider.close()


async def test_unit_it_will_setup_the_pool_only_once(
    mocker: MockerFixture,
) -> None:
    """Test a cursor can be acquired directly."""
    pool = mocker.patch(
        "gdcutils.db.postgres.interfaces.pool.AsyncConnectionPool",
        return_value=MockAsyncPool(),
    )

    async with pg_fastapi_lifespan(app=FastAPI()):
        async with pg_cursor():
            pass

        async with pg_cursor():
            assert pool.call_count == 1


async def test_unit_it_can_get_cursor_reusing_another_conn(
    mocker: MockerFixture,
) -> None:
    """Test a cursor can be acquired by leveraging existing connection."""
    pool = MockAsyncPool()
    mocker.patch(
        "gdcutils.db.postgres.interfaces.pool.AsyncConnectionPool",
        return_value=pool,
    )

    async with pg_fastapi_lifespan(app=FastAPI()):
        async with pg_conn() as conn:
            async with pg_cursor(connection=conn):
                # We expect a single call to .connection
                assert pool.conn_count == 1


async def test_unit_it_can_accept_pydantic_models(
    mocker: MockerFixture,
) -> None:
    """Test a cursor can be acquired directly."""
    pool = MockAsyncPool()
    mocker.patch(
        "gdcutils.db.postgres.interfaces.pool.AsyncConnectionPool",
        return_value=pool,
    )

    class MyData(BaseModel):
        """Test Model"""

    async with pg_fastapi_lifespan(app=FastAPI()):
        async with pg_cursor(dataclass=MyData):
            mock_conn = cast(MockConn, pool.connect)  # type: ignore[redundant-cast]
            assert mock_conn.factory_type
            assert "class_row" in mock_conn.factory_type


async def test_unit_it_will_translate_integrity_error_exceptions(
    mocker: MockerFixture,
) -> None:
    """Test it can connect to PostgreSQL without a specific database."""
    mocker.patch(
        "gdcutils.db.postgres.interfaces.pool.AsyncConnectionPool",
        return_value=MockAsyncPool(),
    )

    with pytest.raises(PgConstraintViolation):
        async with pg_cursor():
            raise psycopg.errors.IntegrityError()
