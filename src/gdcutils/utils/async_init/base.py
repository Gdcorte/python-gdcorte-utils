"""Basic Class definition and handlers."""

import abc
import inspect
from functools import wraps
from typing import Any, AsyncGenerator, Awaitable, Callable, Concatenate, ParamSpec, TypeVar, cast, overload

from gdcutils.utils.async_init.exceptions import AsyncInitImproperError

P = ParamSpec("P")
T = TypeVar("T")
C = TypeVar("C", bound="AsyncInitClass")

AsyncFuncType = Callable[Concatenate[C, P], Awaitable[T]]
AsyncGenType = Callable[Concatenate[C, P], AsyncGenerator[T]]


class AsyncInitClass(abc.ABC):
    """Base interface to enable an async pseudo-init (called _setup)"""

    _client: Any  # Child classes must narrow down the client type

    @abc.abstractmethod
    async def _setup(self) -> None:
        """Async setup meant to replace __init__ limitation on async handling."""

    @staticmethod
    async def _auto_load(state: AsyncInitClass, f: Callable[..., Any], raise_on_not_loaded: bool = False) -> None:
        """Internal client checker"""

        if getattr(state, "_client", None) is None:
            if raise_on_not_loaded:
                msg = inspect.cleandoc(f"""
                        {f.__name__} - {str(f.__class__)}
                        was not correctly initiated. 
                        _setup was not properly executed
                    """)
                raise AsyncInitImproperError(log_msg=msg)

            # Auto-loads the setup method. Since we are, technically,
            # calling class protected members from a static method that does not hold the
            # current instance state, we need to disable protected access...
            # pylint: disable=protected-access
            await state._setup()

    @overload
    @staticmethod
    def validate_setup(
        func: AsyncFuncType[C, P, T],
        *,
        auto_raise: bool = False,
    ) -> AsyncFuncType[C, P, T]: ...

    @overload
    @staticmethod
    def validate_setup(
        func: None = None,
        *,
        auto_raise: bool = False,
    ) -> Callable[[AsyncFuncType[C, P, T]], AsyncFuncType[C, P, T]]: ...

    @staticmethod
    def validate_setup(
        func: AsyncFuncType[C, P, T] | None = None,
        *,
        auto_raise: bool = False,
    ) -> AsyncFuncType[C, P, T] | Callable[[AsyncFuncType[C, P, T]], AsyncFuncType[C, P, T]]:
        """Decorator to ensure class is correctly setup for awaitable functions."""

        def decorator(
            f: AsyncFuncType[C, P, T],
        ) -> AsyncFuncType[C, P, T]:
            @wraps(f)
            async def wrapper(
                self: C,
                *args: P.args,
                **kwargs: P.kwargs,
            ) -> T:
                await AsyncInitClass._auto_load(state=self, f=f, raise_on_not_loaded=auto_raise)
                return await f(self, *args, **kwargs)

            # Auto-typing gets messed up due to the self separation from P.
            # Static typing was never meant to deal with this.
            # And if we embed C onto args (pulling from  args[0]),we lose the base class binding...
            return cast(Callable[Concatenate[C, P], Awaitable[T]], wrapper)

        if func is not None:
            return decorator(func)

        return decorator

    @overload
    @staticmethod
    def validate_ctx_setup(
        func: AsyncGenType[C, P, T],
        *,
        auto_raise: bool = False,
    ) -> AsyncGenType[C, P, T]: ...

    @overload
    @staticmethod
    def validate_ctx_setup(
        func: None = None,
        *,
        auto_raise: bool = False,
    ) -> Callable[[AsyncGenType[C, P, T]], AsyncGenType[C, P, T]]: ...

    @staticmethod
    def validate_ctx_setup(
        func: AsyncGenType[C, P, T] | None = None,
        *,
        auto_raise: bool = False,
    ) -> AsyncGenType[C, P, T] | Callable[[AsyncGenType[C, P, T]], AsyncGenType[C, P, T]]:
        """Decorator to ensure class is correctly setup for awaitable functions."""

        def decorator(
            f: AsyncGenType[C, P, T],
        ) -> AsyncGenType[C, P, T]:
            @wraps(f)
            async def wrapper(
                self: C,
                *args: P.args,
                **kwargs: P.kwargs,
            ) -> AsyncGenerator[T]:
                await AsyncInitClass._auto_load(state=self, f=f, raise_on_not_loaded=auto_raise)

                # Stream the results out via async for / yield
                async for item in f(self, *args, **kwargs):
                    yield item

            return cast(Callable[Concatenate[C, P], AsyncGenerator[T]], wrapper)

        if func is not None:
            return decorator(func)

        return decorator
