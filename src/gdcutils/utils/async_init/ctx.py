"""Contextual based classes.

Forces class functionalities to be called from a context.

Assuming a base standard protocol is followed, we can ensure
that the async classes follow a predictable pattern and know when
the setup is proper.

It attempt to force a context assuming that the class setup is called
exclusively in the __aenter__ method.
"""

from types import TracebackType
from typing import Self, Type

from gdcutils.utils.async_init.base import AsyncInitClass


class AsyncCtxClass(AsyncInitClass):
    """Async initiable class with contextual support.

    Setup is self-run upon context enter, if not overriden.
    """

    async def __aenter__(self) -> Self:
        """Context binding."""
        await self._setup()

        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """On context exit.

        Override this to provide proper, customized teardown
        for your class.
        """
        # bubble up unhandled exceptions.
        return False
