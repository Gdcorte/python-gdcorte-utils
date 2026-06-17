"""Postgre direct connection interface."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TypeVar, overload

from psycopg import AsyncConnection, AsyncCursor
from psycopg.rows import BaseRowFactory, DictRow, TupleRow, class_row, dict_row
from pydantic import BaseModel

from gdcutils.db.postgres.config import PgConnectionParams
from gdcutils.db.postgres.interfaces.contract import PgInterface
from gdcutils.utils.singleton import Singleton

T = TypeVar("T", bound=BaseModel)


class PgConnProvider(PgInterface, metaclass=Singleton):
    """PostgreSQL connection pool singleton"""

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[AsyncConnection[TupleRow]]:
        """Receive a connection object to the database"""

        creds = PgConnectionParams()
        async with await AsyncConnection.connect(
            **creds.model_serialize(),
        ) as conn:
            yield conn

    @asynccontextmanager
    async def _conn_handler(
        self,
        connection: AsyncConnection | None,
    ) -> AsyncGenerator[AsyncConnection[TupleRow]]:
        if connection is None:
            async with self.connect() as conn:
                yield conn
        else:
            yield connection

    @overload
    @asynccontextmanager
    def cursor(
        self,
        dataclass: type[T],
        connection: AsyncConnection | None = None,
    ) -> AsyncGenerator[AsyncCursor[T]]: ...

    @overload
    @asynccontextmanager
    def cursor(
        self,
        dataclass: None = None,
        connection: AsyncConnection | None = None,
    ) -> AsyncGenerator[AsyncCursor[DictRow]]: ...

    @asynccontextmanager
    async def cursor(
        self,
        dataclass: type[T] | None = None,
        connection: AsyncConnection | None = None,
    ) -> AsyncGenerator[AsyncCursor[T | DictRow]]:
        """Yields a cursor, either from a connection or directly from the pool"""
        cursor_row: BaseRowFactory[T | DictRow] = dict_row
        if dataclass is not None:
            cursor_row = class_row(dataclass)

        # pylint: disable=contextmanager-generator-missing-cleanup
        async with self._conn_handler(connection) as conn:
            async with conn.cursor(row_factory=cursor_row) as cursor:
                yield cursor

    async def close(self) -> None:
        """Closes the connection pool"""
