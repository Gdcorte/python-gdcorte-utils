"""Postgre pool interface."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from psycopg.rows import TupleRow
from psycopg_pool import AsyncConnectionPool

from gdcutils.db.postgres.config import PgConnectionParams, PgPoolSettings
from gdcutils.db.postgres.interfaces.conn import PgConnProvider


class PgPoolProvider(PgConnProvider):
    """PostgreSQL connection pool singleton.

    It builds on top of the raw connection provider to get the
    connection from the pool instead of making a new one.
    the rest is the same...
    """

    _client: AsyncConnectionPool | None
    _lock: asyncio.Lock

    def __init__(self) -> None:
        """Constructor."""
        super().__init__()

        self._lock = asyncio.Lock()
        self._client = None

    async def _setup(
        self,
    ) -> AsyncConnectionPool:
        """Setup method for internal pool client.

        Creds and Config are not everrideable, please
        change them from the environment instead.
        """
        creds = PgConnectionParams()
        config = PgPoolSettings()

        client = AsyncConnectionPool(
            kwargs=creds.model_serialize(),
            **config.model_dump(mode="json"),
            open=False,
        )

        # We can't open in instantiation, but we can open right after...
        await client.open()

        return client

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[AsyncConnection[TupleRow]]:
        """Gets a connection from the pool"""

        async with self._lock:
            if self._client is None or self._client.closed:
                # If we hit this block, the internal client is
                # effectively busted or never initialized...
                # We need to make a new one...
                self._client = await self._setup()
            else:
                # Ensure we will refresh credentials in case of rotation.
                # This assumes proper integration between SSM Parameter store and
                # your application to auto-refresh the environment
                creds = PgConnectionParams()
                self._client.kwargs = creds.model_serialize()

        async with self._client.connection() as conn:
            yield conn

    async def close(self) -> None:
        """Closes the connection pool"""
        if self._client is None:
            return

        if not self._client.closed:
            await self._client.close()
