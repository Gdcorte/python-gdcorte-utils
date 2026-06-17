"""Handy Utilities built on top of the service."""


# async def pg_insert_single(
#     dataclass: type[T],
#     data: T,
#     table_name: str,
# ) -> None:
#     await pg_insert_multiple(
#         dataclass=dataclass,
#         data=[data],
#         table_name=table_name,
#     )


# async def pg_insert_multiple(
#     dataclass: type[T],
#     data: Sequence[T],
#     table_name: str,
#     conn: AsyncConnection | None = None,
# ) -> None:
#     fields = list(dataclass.model_fields.keys())

#     line_placeholder = psycopg.sql.SQL(", ").join(psycopg.sql.Placeholder() * len(fields))
#     field_placeholders = psycopg.sql.SQL("({})").format(line_placeholder)

#     values: list[str] = []
#     for data_row in data:
#         link_json = data_row.model_dump(mode="json")
#         ordered_values = [link_json[field_name] for field_name in fields]

#         values.extend(ordered_values)

#     values_placeholder = psycopg.sql.SQL(", ").join([field_placeholders] * len(data))

#     sql = psycopg.sql.SQL(
#         """
#         INSERT INTO {table_name}
#             ({fields})
#         VALUES
#             {placeholders}
#     """
#     ).format(
#         table_name=psycopg.sql.Identifier(table_name),
#         fields=psycopg.sql.SQL(", ").join(map(psycopg.sql.Identifier, fields)),
#         placeholders=values_placeholder,
#     )
#     sql_params = values

#     async with pg_cursor(dataclass=dataclass, connection=conn) as cursor:
#         await cursor.execute(sql, sql_params)
