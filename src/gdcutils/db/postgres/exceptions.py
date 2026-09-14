"""PostgreSQL Extended Exceptions."""

import re
from typing import Unpack

import psycopg
from fastapi import status

from gdcutils.http.exceptions import HttpBaseException, HttpBaseExcKwargs


class PgBaseError(HttpBaseException):
    """Base PostgreSQL Exception"""

    def __init__(
        self,
        exc: psycopg.Error | None = None,
        **kwargs: Unpack[HttpBaseExcKwargs],
    ):
        kwargs.setdefault("err_group", "pg_db_unknown_error")
        kwargs.setdefault("err_code", "unkonwn_error")
        kwargs.setdefault("status", status.HTTP_400_BAD_REQUEST)

        if exc is not None:
            kwargs.setdefault("log_msg", str(exc))

        super().__init__(**kwargs)


class PgConstraintViolation(PgBaseError):
    """PostgreSQL Constraint Violation Exception"""

    exc: psycopg.errors.IntegrityError
    diag: psycopg.errors.Diagnostic

    def __init__(
        self,
        exc: psycopg.errors.IntegrityError,
        **kwargs: Unpack[HttpBaseExcKwargs],
    ):
        name = type(exc).__name__
        code = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

        kwargs.setdefault("err_group", "pg_db_integrity_error")
        kwargs.setdefault("err_code", code)
        kwargs.setdefault("log_msg", str(exc.diag))

        super().__init__(exc, **kwargs)
