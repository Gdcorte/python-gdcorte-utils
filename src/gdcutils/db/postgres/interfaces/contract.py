"""Base contract between Pool and Connection providers."""

import abc
from collections.abc import Awaitable
from contextlib import AbstractAsyncContextManager
from typing import TypeVar, overload

from psycopg import AsyncConnection, AsyncCursor
from psycopg.rows import DictRow, TupleRow
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class PgInterface(abc.ABC):
    """Base Interface with standard operations."""

    @abc.abstractmethod
    def connect(self) -> AbstractAsyncContextManager[AsyncConnection[TupleRow]]:
        """Receive a connection object to the database"""

    @overload
    def cursor(
        self,
        dataclass: type[T],
        connection: AsyncConnection | None = None,
    ) -> AbstractAsyncContextManager[AsyncCursor[T]]: ...

    @overload
    def cursor(
        self,
        dataclass: None = None,
        connection: AsyncConnection | None = None,
    ) -> AbstractAsyncContextManager[AsyncCursor[DictRow]]: ...

    @abc.abstractmethod
    def cursor(
        self,
        dataclass: type[T] | None = None,
        connection: AsyncConnection | None = None,
    ) -> AbstractAsyncContextManager[AsyncCursor[T | DictRow]]:
        """Yields a cursor, either from a connection or directly from the pool"""

    @abc.abstractmethod
    def close(self) -> Awaitable[None]:
        """Closes the connection pool"""
