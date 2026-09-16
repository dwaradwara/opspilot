import json
import logging

from app.core.logging import JsonFormatter


def _format_record(
    message: str,
    **extra,
) -> dict:
    record = logging.LogRecord(
        name="opspilot.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )

    for key, value in extra.items():
        setattr(record, key, value)

    return json.loads(
        JsonFormatter().format(record)
    )


def test_redacts_password_from_database_url() -> None:
    payload = _format_record(
        "connection failed: "
        "postgresql://opspilot:super-secret-password@db:5432/opspilot"
    )

    message = payload["message"]

    assert "super-secret-password" not in message
    assert (
        "postgresql://opspilot:[REDACTED]@db:5432/opspilot"
        in message
    )


def test_redacts_tokens_and_key_value_secrets() -> None:
    payload = _format_record(
        'payload={"password":"hunter2","api_key":"key-123"} '
        "Authorization: Bearer abc.def.ghi"
    )

    message = payload["message"]

    assert "hunter2" not in message
    assert "key-123" not in message
    assert "abc.def.ghi" not in message
    assert message.count("[REDACTED]") >= 3


def test_redacts_exception_message() -> None:
    payload = _format_record(
        "request failed",
        exception_type="RuntimeError",
        exception_message=(
            "authentication failed password=very-secret-value"
        ),
    )

    assert (
        "very-secret-value"
        not in payload["exception_message"]
    )
    assert "[REDACTED]" in payload["exception_message"]


def test_preserves_non_sensitive_log_content() -> None:
    payload = _format_record(
        "ticket processing failed",
        request_id="req-123",
        exception_type="RuntimeError",
    )

    assert payload["message"] == "ticket processing failed"
    assert payload["request_id"] == "req-123"
    assert payload["exception_type"] == "RuntimeError"
