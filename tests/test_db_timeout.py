import time

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import settings
from app.db.session import engine


@pytest.mark.asyncio
async def test_postgres_statement_timeout_cancels_long_query():
    started = time.perf_counter()

    try:
        with pytest.raises(DBAPIError) as exc_info:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT pg_sleep(10)"))

        elapsed = time.perf_counter() - started

        assert elapsed >= settings.db_statement_timeout_seconds * 0.8
        assert elapsed < settings.db_statement_timeout_seconds + 2.0
        assert "statement timeout" in str(exc_info.value).lower()

    finally:
        # The application engine is module-scoped. This test runs under
        # pytest-asyncio while FastAPI TestClient uses another event loop.
        # Dispose pooled asyncpg connections so later tests reconnect on
        # their own event loop.
        await engine.dispose()