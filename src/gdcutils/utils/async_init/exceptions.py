"""Async init exceptions."""

from typing import Unpack

from gdcutils.http.exceptions import HttpBaseException, HttpBaseExcKwargs


class AsyncInitError(HttpBaseException):
    """Base ctx error class."""

    def __init__(self, **kwargs: Unpack[HttpBaseExcKwargs]):
        kwargs.setdefault("err_group", "async_init_error")
        kwargs.setdefault("err_code", "unknown_error")
        super().__init__(**kwargs)


class AsyncInitImproperError(AsyncInitError):
    """Base ctx error class."""

    def __init__(self, **kwargs: Unpack[HttpBaseExcKwargs]):
        kwargs.setdefault("err_group", "instance_invokation_error")
        kwargs.setdefault("err_code", "instance_without_proper_setup")
        super().__init__(**kwargs)
