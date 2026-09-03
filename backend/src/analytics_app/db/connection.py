from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import psycopg
from psycopg.conninfo import make_conninfo

from analytics_app.domain.models import DatabaseConfigInput


def connection_string(config: DatabaseConfigInput) -> str:
    return make_conninfo(
        host=config.host,
        port=config.port,
        dbname=config.database,
        user=config.username,
        password=config.password.get_secret_value() if config.password else "",
        sslmode=config.sslmode,
        connect_timeout=min(config.timeout_seconds, 30),
        application_name="datapilot-readonly",
    )


@asynccontextmanager
async def open_connection(
    config: DatabaseConfigInput,
) -> AsyncIterator[psycopg.AsyncConnection[Any]]:
    connection = await psycopg.AsyncConnection.connect(connection_string(config))
    try:
        yield connection
    finally:
        await connection.close()


async def test_connection(config: DatabaseConfigInput) -> dict[str, str]:
    async with open_connection(config) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT current_database(), current_user")
            row = await cursor.fetchone()
            if row is None:
                return {"database": "", "user": "", "status": "error"}
            database, user = row
            return {"database": str(database), "user": str(user), "status": "ok"}
