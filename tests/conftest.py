"""Tests setup configuration."""

from typing import Iterator

import pytest
from dotenv import load_dotenv


@pytest.fixture(autouse=True)
def setup() -> Iterator[None]:
    """Load test environment variables"""
    load_dotenv(".env.example", override=True)

    yield
