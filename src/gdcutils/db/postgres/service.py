"""Postgre conn/cursor service."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Type, TypeVar, overload

import psycopg
from fastapi import FastAPI
from psycopg import AsyncConnection, AsyncCursor
from psycopg.rows import DictRow, TupleRow
from pydantic import BaseModel

from gdcutils.db.postgres.config import PgServiceOptions
from gdcutils.db.postgres.exceptions import PgConstraintViolation
from gdcutils.db.postgres.interfaces.conn import PgConnProvider
from gdcutils.db.postgres.interfaces.contract import PgInterface
from gdcutils.db.postgres.interfaces.pool import PgPoolProvider

T = TypeVar("T", bound=BaseModel)


def _pg_interface_factory() -> Type[PgInterface]:
    """Switches between Pool or direct connection for PG interface.

    Returns
    -------
        The resolved interface
    """
    options = PgServiceOptions()

    provider: Type[PgInterface] = PgPoolProvider
    if options.disable_pool:
        provider = PgConnProvider

    return provider


@asynccontextmanager
async def pg_conn() -> AsyncGenerator[AsyncConnection[TupleRow]]:
    """Yield a connection object for DB communication.

    Interface (Pool / Conn) will be detected based on settings.
    THey can be customized by setting specific env vars.
    By default, will use a Pool.

    Yields
    ------
        A connection to be used
    """
    provider = _pg_interface_factory()

    async with provider().connect() as conn:
        yield conn


@overload
@asynccontextmanager
def pg_cursor(
    dataclass: type[T],
    connection: AsyncConnection | None = None,
) -> AsyncGenerator[AsyncCursor[T]]: ...


@overload
@asynccontextmanager
def pg_cursor(
    dataclass: None = None,
    connection: AsyncConnection | None = None,
) -> AsyncGenerator[AsyncCursor[DictRow]]: ...


@asynccontextmanager
async def pg_cursor(
    dataclass: type[T] | None = None,
    connection: AsyncConnection | None = None,
) -> AsyncGenerator[AsyncCursor[T | DictRow]]:
    """Yields a cursor for database operations.

    Parameters
    ----------
    dataclass, optional
        Custom pydantic model to bind the response.
        Psycopg will automatically coerce SELECT results into
        provided dataclass,
        If not provided, defaults to returning a standard dictionary on
        SELECTs. By default None
    connection, optional
        Re-use a connection to yield a cursor. One conn can have many cursors.
        The opposite is not true.
         If ommited, a new/free connection is used. By default None

    Yields
    ------
        The assigned cursor. Either bound or unbound to the provided dataclass.

    Raises
    ------
    PgConstraintViolation
        If there is a psycopg exceptions, translate it into the streamlined
        http exceptions for log and treatment down the pipe.
    """

    # If we do not need the connect method altogether.
    provider: Type[PgInterface] = PgConnProvider
    if connection is None:
        provider = _pg_interface_factory()

    async with provider().cursor(connection=connection, dataclass=dataclass) as cursor:
        try:
            yield cursor

        except psycopg.errors.IntegrityError as exc:
            raise PgConstraintViolation(exc=exc) from exc


@asynccontextmanager
async def pg_pool_lifespan() -> AsyncGenerator[None]:
    """Manages the pool lifespan and closes it at the end of life.

    The pool must be closed, otherwise your app will hang on forever.
    This gurantees that the provider will be properly closed at the end
    of its intended execution.
    """
    provider = _pg_interface_factory()()

    try:
        yield

    finally:
        await provider.close()


@asynccontextmanager
async def pg_fastapi_lifespan(
    app: FastAPI,  # pylint: disable=unused-argument
) -> AsyncGenerator[None]:
    """Lifespan manager for FastAPI to ensure proper closure on app unmount."""
    async with pg_pool_lifespan():
        yield
