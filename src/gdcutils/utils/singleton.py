"""True singleton utility"""

import abc
import threading
from typing import Any, Type, TypeVar, cast

# This kind of bonding will not let us define the type in the
# _instances class var. This means some type hack will be in play
T = TypeVar("T", bound="Singleton")


class Singleton(abc.ABCMeta):
    """Metaclass to ensure a single instance exists"""

    # Instance control
    _instances: dict[Type[Any] | str, Any] = {}
    _locks: dict[Type[Any] | str, Any] = {}
    _global_lock = threading.Lock()

    def __call__(  # type: ignore[misc]
        cls: Type[T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Control method for instantiating new singletons"""

        # singleton_key: str | Type[T]
        singleton_key = cls

        if cls not in cls._locks:
            with cls._global_lock:
                if cls not in cls._locks:
                    cls._locks[cls] = threading.Lock()

        # Double checked locking design to improve performance
        if singleton_key not in cls._instances:
            with cls._locks[cls]:
                if singleton_key not in cls._instances:
                    instance = super(Singleton, cls).__call__(*args, **kwargs)
                    cls._instances[singleton_key] = instance

        # We need this here for correctly reverse-mapping the types
        return cast(T, cls._instances[cls])
