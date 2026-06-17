"""Test Async init class and its ctx child."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest

from gdcutils.utils.async_init.base import AsyncInitClass
from gdcutils.utils.async_init.ctx import AsyncCtxClass
from gdcutils.utils.async_init.exceptions import AsyncInitImproperError


async def test_unit_it_can_auto_call_for_method() -> None:
    """Test that it can raise for marked methods when not properly setup."""

    class MyLittleTest(AsyncInitClass):
        """Test Class."""

        count: int

        def __init__(self) -> None:
            super().__init__()

            self.count = 0

        async def _setup(self) -> None:
            "The SETUP."
            self.count += 1

        @AsyncInitClass.validate_setup
        async def protected_method(self) -> None:
            """No need to have anything here yet."""

    instance = MyLittleTest()

    await instance.protected_method()
    assert instance.count > 0


async def test_unit_it_can_raise_for_method_when_setup_is_not_called() -> None:
    """Test that it can raise for marked methods when not properly setup."""

    class MyLittleTest(AsyncInitClass):
        """Test Class."""

        async def _setup(self) -> None:
            "The SETUP."

        @AsyncInitClass.validate_setup(auto_raise=True)
        async def protected_method(self) -> None:
            """No need to have anything here yet."""

    instance = MyLittleTest()

    with pytest.raises(AsyncInitImproperError):
        await instance.protected_method()


async def test_unit_it_can_auto_call_for_generator() -> None:
    """Test that it can raise for marked methods when not properly setup."""

    class MyLittleTest(AsyncInitClass):
        """Test Class."""

        count: int

        def __init__(self) -> None:
            super().__init__()

            self.count = 0

        async def _setup(self) -> None:
            "The SETUP."
            self.count += 1

        @asynccontextmanager
        @AsyncInitClass.validate_ctx_setup
        async def protected_method(self) -> AsyncGenerator[None]:
            """No need to have anything useful here yet."""

            yield

    instance = MyLittleTest()

    async with instance.protected_method():
        pass

    assert instance.count > 0


async def test_unit_it_can_raise_for_generator_when_setup_is_not_called() -> None:
    """Test that it can raise for marked methods when not properly setup."""

    class MyLittleTest(AsyncInitClass):
        """Test Class."""

        async def _setup(self) -> None:
            "The SETUP."

        @asynccontextmanager
        @AsyncInitClass.validate_ctx_setup(auto_raise=True)
        async def protected_method(self) -> AsyncGenerator[None]:
            """No need to have anything useful here yet."""

            yield

    instance = MyLittleTest()

    with pytest.raises(AsyncInitImproperError):
        async with instance.protected_method():
            pass


async def test_unit_it_can_be_initialized_as_context_with_auto_setup() -> None:
    """Test ctx child class can be a auto-setup context."""

    class MyLittleTest(AsyncCtxClass):
        """Test Class."""

        count: int

        def __init__(self) -> None:
            super().__init__()

            self.count = 0

        async def _setup(self) -> None:
            "The SETUP."
            self.count += 1

    async with MyLittleTest() as instance:
        assert instance.count > 0
