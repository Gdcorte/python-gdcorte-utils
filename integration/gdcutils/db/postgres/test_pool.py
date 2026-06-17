"""Test pool-based database manipulation."""

import pytest
from dotenv import load_dotenv
from fastapi import FastAPI
from psycopg import AsyncConnection

from gdcutils.db.postgres import pg_conn, pg_fastapi_lifespan, pg_pool_lifespan


async def test_integ_can_connect_using_pool_with_db() -> None:
    """Test it can connect to PostgreSQL using a specific database."""
    load_dotenv(override=True)

    async with pg_fastapi_lifespan(app=FastAPI()):
        async with pg_conn() as conn:
            assert isinstance(conn, AsyncConnection)


async def test_integ_can_connect_using_pool_with_no_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test it can connect to PostgreSQL without a specific database."""
    load_dotenv(override=True)

    monkeypatch.delenv("PG_DB")

    async with pg_pool_lifespan():
        async with pg_conn() as conn:
            assert isinstance(conn, AsyncConnection)
