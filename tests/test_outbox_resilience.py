import asyncio

import pytest

from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)
from app.services import outbox_dispatcher


class FakeRedis:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    async def rpush(self, key, payload):
        self.calls += 1

        outcome = self.outcomes.pop(0)

        if isinstance(outcome, BaseException):
            raise outcome

        return outcome


@pytest.mark.asyncio
async def test_publish_succeeds_on_first_attempt(monkeypatch):
    monkeypatch.setattr(
        outbox_dispatcher.settings,
        "redis_retry_attempts",
        2,
    )

    redis = FakeRedis([1])

    failed_attempts = await outbox_dispatcher.publish_with_retry(
        redis=redis,
        message_payload={"ticket_id": "123"},
        event_id="event-1",
        event_type="ticket.created",
    )

    assert failed_attempts == 0
    assert redis.calls == 1


@pytest.mark.asyncio
async def test_publish_retries_after_timeout_and_recovers(monkeypatch):
    monkeypatch.setattr(
        outbox_dispatcher.settings,
        "redis_retry_attempts",
        2,
    )
    monkeypatch.setattr(
        outbox_dispatcher.settings,
        "redis_retry_base_delay_seconds",
        0,
    )
    monkeypatch.setattr(
        outbox_dispatcher.settings,
        "redis_retry_max_delay_seconds",
        0,
    )

    redis = FakeRedis(
        [
            asyncio.TimeoutError(),
            1,
        ]
    )

    failed_attempts = await outbox_dispatcher.publish_with_retry(
        redis=redis,
        message_payload={"ticket_id": "123"},
        event_id="event-2",
        event_type="ticket.created",
    )

    assert failed_attempts == 1
    assert redis.calls == 2


@pytest.mark.asyncio
async def test_publish_exhausts_retries_on_timeout(monkeypatch):
    monkeypatch.setattr(
        outbox_dispatcher.settings,
        "redis_retry_attempts",
        2,
    )
    monkeypatch.setattr(
        outbox_dispatcher.settings,
        "redis_retry_base_delay_seconds",
        0,
    )
    monkeypatch.setattr(
        outbox_dispatcher.settings,
        "redis_retry_max_delay_seconds",
        0,
    )

    redis = FakeRedis(
        [
            asyncio.TimeoutError(),
            asyncio.TimeoutError(),
            asyncio.TimeoutError(),
        ]
    )

    with pytest.raises(asyncio.TimeoutError):
        await outbox_dispatcher.publish_with_retry(
            redis=redis,
            message_payload={"ticket_id": "123"},
            event_id="event-3",
            event_type="ticket.created",
        )

    assert redis.calls == 3


def test_circuit_breaker_opens_after_failure_threshold(monkeypatch):
    now = [100.0]

    monkeypatch.setattr(
        "app.core.circuit_breaker.monotonic",
        lambda: now[0],
    )

    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_seconds=10,
    )

    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure()

    assert breaker.state == CircuitState.OPEN
    assert breaker.failure_count == 2

    with pytest.raises(CircuitBreakerOpenError):
        breaker.before_request()


def test_circuit_breaker_recovers_after_timeout(monkeypatch):
    now = [100.0]

    monkeypatch.setattr(
        "app.core.circuit_breaker.monotonic",
        lambda: now[0],
    )

    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_seconds=10,
    )

    breaker.record_failure()
    breaker.record_failure()

    assert breaker.state == CircuitState.OPEN

    now[0] = 111.0

    breaker.before_request()

    assert breaker.state == CircuitState.HALF_OPEN

    breaker.record_success()

    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


def test_half_open_failure_reopens_circuit(monkeypatch):
    now = [100.0]

    monkeypatch.setattr(
        "app.core.circuit_breaker.monotonic",
        lambda: now[0],
    )

    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_seconds=10,
    )

    breaker.record_failure()
    breaker.record_failure()

    now[0] = 111.0

    breaker.before_request()

    assert breaker.state == CircuitState.HALF_OPEN

    breaker.record_failure()

    assert breaker.state == CircuitState.OPEN

    with pytest.raises(CircuitBreakerOpenError):
        breaker.before_request()
