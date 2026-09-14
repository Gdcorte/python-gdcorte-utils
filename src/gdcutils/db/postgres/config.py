"""postgreSQL configration models."""

from enum import StrEnum
from typing import Any, Callable

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class PgSerializeModes(StrEnum):
    """Serialization options for DB params"""

    CONNSTR = "conn_str"


class PgConnectionParams(BaseSettings):
    """PostgreSQL connect parameters model"""

    model_config = SettingsConfigDict(
        env_prefix="PG_",
        extra="ignore",
        populate_by_name=True,
    )

    user: str
    password: SecretStr
    host: str
    port: int
    dbname: str | None = Field(
        default="postgres",
        validation_alias=AliasChoices(
            "pg_db",
            "db",
            "schema",
        ),
    )

    def serializer_conn_str(self) -> dict[str, str | int]:
        """Serialize this model into a psycopg conn parametrized dict."""

        params = self.model_dump(mode="json", exclude_none=True)
        params["password"] = self.password.get_secret_value()

        return params

    def model_serialize(
        self,
        mode: PgSerializeModes = PgSerializeModes.CONNSTR,
    ) -> dict[str, Any]:
        """Serialize the data into a compliant mode."""

        serialization_map: dict[PgSerializeModes, Callable[[], dict[str, Any]]] = {
            PgSerializeModes.CONNSTR: self.serializer_conn_str,
        }

        handler = serialization_map.get(mode, self.model_dump)
        return handler()


class PgPoolSettings(BaseSettings):
    """Pool configuration settings"""

    model_config = SettingsConfigDict(
        env_prefix="PG_POOL_",
        extra="ignore",
    )

    min_size: int = 1
    max_size: int = 10


class PgServiceOptions(BaseSettings):
    """Service level options"""

    model_config = SettingsConfigDict(
        env_prefix="PG_OPTIONS_",
        extra="ignore",
    )

    disable_pool: bool = False
