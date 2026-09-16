import json
import logging
import re
from datetime import datetime, timezone

from opentelemetry import trace

from app.core.config import settings


REDACTED = "[REDACTED]"

_SENSITIVE_KEY_PATTERN = re.compile(
    r"""(?ix)
    (?P<prefix>
        ["']?
        (?:
            password
            | passwd
            | pwd
            | database_password
            | secret
            | jwt_secret
            | token
            | access_token
            | refresh_token
            | api[_-]?key
            | apikey
            | authorization
        )
        ["']?
        \s*[:=]\s*
    )
    (?:
        (?P<quote>["'])
        (?P<quoted_value>[^"']*)
        (?P=quote)
        |
        (?P<plain_value>[^\s,;}&]+)
    )
    """
)

_BEARER_PATTERN = re.compile(
    r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"
)

_URL_CREDENTIAL_PATTERN = re.compile(
    r"(?P<prefix>\b[a-z][a-z0-9+.-]*://[^:/@\s]+:)"
    r"(?P<secret>[^@/\s]+)"
    r"(?=@)"
)


def redact_secrets(value: str) -> str:
    text = value

    # Remove exact application secrets if they ever appear in a message.
    for secret in (
        getattr(settings, "database_password", None),
        getattr(settings, "jwt_secret", None),
    ):
        if secret and len(secret) >= 8:
            text = text.replace(secret, REDACTED)

    # postgresql://user:password@host
    text = _URL_CREDENTIAL_PATTERN.sub(
        lambda match: f"{match.group('prefix')}{REDACTED}",
        text,
    )

    # Authorization: Bearer <token>
    text = _BEARER_PATTERN.sub(
        f"Bearer {REDACTED}",
        text,
    )

    # password=..., token=..., "api_key":"...", etc.
    def redact_key_value(match: re.Match) -> str:
        prefix = match.group("prefix")
        quote = match.group("quote")

        if quote:
            return f"{prefix}{quote}{REDACTED}{quote}"

        return f"{prefix}{REDACTED}"

    return _SENSITIVE_KEY_PATTERN.sub(
        redact_key_value,
        text,
    )


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_secrets(record.getMessage()),
        }

        span_context = trace.get_current_span().get_span_context()

        if span_context.is_valid:
            payload["trace_id"] = format(
                span_context.trace_id,
                "032x",
            )
            payload["span_id"] = format(
                span_context.span_id,
                "016x",
            )

        for field in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "user_id",
            "organization_id",
            "exception_type",
            "exception_message",
        ):
            value = getattr(record, field, None)

            if value is not None:
                if isinstance(value, str):
                    value = redact_secrets(value)

                payload[field] = value

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())
