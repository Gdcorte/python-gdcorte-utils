"""Test connection-based database manipulation."""

import pytest
from dotenv import load_dotenv
from pytest_mock import MockerFixture

from gdcutils.db.postgres import pg_conn


async def test_unit_it_can_connect_using_connection_with_db(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
) -> None:
    """Test it can connect to PostgreSQL using a specific database."""
    load_dotenv(override=True)

    monkeypatch.setenv("PG_OPTIONS_DISABLE_POOL", "true")

    conn = mocker.patch("gdcutils.db.postgres.interfaces.conn.AsyncConnection.connect")

    async with pg_conn():
        assert conn.call_count == 1


async def test_unit_it_can_connect_using_connection_with_no_db(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
) -> None:
    """Test it can connect to PostgreSQL without a specific database."""
    load_dotenv(override=True)
    conn = mocker.patch("gdcutils.db.postgres.interfaces.conn.AsyncConnection.connect")

    monkeypatch.setenv("PG_OPTIONS_DISABLE_POOL", "true")
    monkeypatch.delenv("PG_DB")

    async with pg_conn():
        assert conn.call_count == 1
