"""DynamoDB Handler"""

# TODO: TEsting!!!!!

from collections.abc import Generator
from contextlib import contextmanager
from typing import Unpack

import boto3
from botocore.exceptions import ClientError
from pydantic_settings import BaseSettings, SettingsConfigDict
from types_boto3_dynamodb.service_resource import Table as DynamoDbTable

from gdcutils.http.exceptions import HttpBaseException, HttpBaseExcKwargs


class DdbBaseError(HttpBaseException):
    """Base DynamoDB Exception"""

    def __init__(self, **kwargs: Unpack[HttpBaseExcKwargs]):
        kwargs.setdefault("err_group", "aws_dynamo_error")
        kwargs.setdefault("err_code", "unknown_error")

        super().__init__(**kwargs)


class DynamoDbClientParams(BaseSettings):
    """DynamoDB configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AWS_DDB_",
        extra="ignore",
        populate_by_name=True,
    )

    name: str
    region: str = "us-east-1"


@contextmanager
def ddb_client(
    settings: DynamoDbClientParams | None = None,
) -> Generator[DynamoDbTable]:
    """DynamoDB client handling.

    Parameters
    ----------
    settings, optional
        Override default settings from environment, by default None

    Yields
    ------
        ddb client through boto3 for use rinteraction.

    Raises
    ------
    DdbBaseError
        If any DDB related error happens during execution of this client.
    """

    if settings is None:
        settings = DynamoDbClientParams()

    client = boto3.resource(
        "dynamodb",
        region_name=settings.region,
    )

    try:
        table = client.Table(settings.name)
        yield table

    except ClientError as exc:
        # Extract error code and message for more specific error handling
        error_code = exc.response.get("Error", {}).get("Code", "Unknown")
        error_message = exc.response.get("Error", {}).get("Message", str(exc))

        raise DdbBaseError(
            user_msg="Unable to perform DDB operation",
            err_code=error_code,
            log_msg=f"{error_code}: {error_message}",
        ) from exc
