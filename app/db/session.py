from collections.abc import AsyncGenerator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.metrics import record_db_error, register_db_pool_metrics


engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout_seconds,
    connect_args={
        "server_settings": {
            "statement_timeout": str(
                int(settings.db_statement_timeout_seconds * 1000)
            ),
        },
    },
)

register_db_pool_metrics(engine, settings.db_max_overflow)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError as exc:
            record_db_error(exc)
            raise