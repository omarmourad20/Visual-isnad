"""Read the installed SQLite schema without changing migration state."""
from django.db import connections


def has_chain_index(alias="default"):
    connection = connections[alias]
    if connection.vendor != "sqlite":
        return True
    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(cursor, "isnad_transmissionedge")
    return any(column.name == "chain_index" for column in columns)
