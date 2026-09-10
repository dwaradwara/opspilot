from prometheus_client import Gauge
from sqlalchemy.ext.asyncio import AsyncEngine


DB_POOL_SIZE = Gauge(
    "opspilot_db_pool_size",
    "Configured SQLAlchemy database connection pool size",
)

DB_POOL_MAX_OVERFLOW = Gauge(
    "opspilot_db_pool_max_overflow",
    "Configured maximum SQLAlchemy pool overflow",
)

DB_POOL_CAPACITY = Gauge(
    "opspilot_db_pool_capacity",
    "Maximum SQLAlchemy database connection capacity",
)

DB_POOL_CHECKED_OUT = Gauge(
    "opspilot_db_pool_checked_out_connections",
    "Number of database connections currently checked out from the pool",
)

DB_POOL_CHECKED_IN = Gauge(
    "opspilot_db_pool_checked_in_connections",
    "Number of idle database connections currently available in the pool",
)

DB_POOL_OVERFLOW = Gauge(
    "opspilot_db_pool_overflow_connections",
    "Number of database connections currently using pool overflow capacity",
)


def register_db_pool_metrics(
    engine: AsyncEngine,
    max_overflow: int,
) -> None:
    pool = engine.sync_engine.pool

    DB_POOL_SIZE.set_function(lambda: pool.size())
    DB_POOL_MAX_OVERFLOW.set(max_overflow)
    DB_POOL_CAPACITY.set_function(lambda: pool.size() + max_overflow)
    DB_POOL_CHECKED_OUT.set_function(lambda: pool.checkedout())
    DB_POOL_CHECKED_IN.set_function(lambda: pool.checkedin())
    DB_POOL_OVERFLOW.set_function(lambda: max(0, pool.overflow()))
