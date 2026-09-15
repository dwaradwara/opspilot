from prometheus_client import REGISTRY
from sqlalchemy.exc import (
    OperationalError,
    SQLAlchemyError,
    TimeoutError as SQLAlchemyTimeoutError,
)

from app.db.metrics import classify_db_error, record_db_error


def test_classify_statement_timeout():
    exc = SQLAlchemyError(
        "canceling statement due to statement timeout"
    )

    assert classify_db_error(exc) == "statement_timeout"


def test_classify_pool_timeout():
    exc = SQLAlchemyTimeoutError(
        "QueuePool limit reached"
    )

    assert classify_db_error(exc) == "pool_timeout"


def test_classify_connection_error():
    exc = OperationalError(
        "SELECT 1",
        {},
        Exception("connection refused"),
    )

    assert classify_db_error(exc) == "connection_error"


def test_classify_generic_database_error():
    exc = SQLAlchemyError(
        "unexpected database failure"
    )

    assert classify_db_error(exc) == "database_error"


def test_record_db_error_increments_prometheus_counter():
    labels = {"error_type": "statement_timeout"}

    before = REGISTRY.get_sample_value(
        "opspilot_db_errors_total",
        labels,
    ) or 0.0

    record_db_error(
        SQLAlchemyError(
            "canceling statement due to statement timeout"
        )
    )

    after = REGISTRY.get_sample_value(
        "opspilot_db_errors_total",
        labels,
    )

    assert after == before + 1.0