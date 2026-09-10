from enum import Enum
from time import monotonic


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    def __init__(self, retry_after_seconds: float) -> None:
        self.retry_after_seconds = max(retry_after_seconds, 0.0)
        super().__init__(
            f"Circuit breaker is open; retry after "
            f"{self.retry_after_seconds:.2f} seconds"
        )


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int,
        recovery_seconds: float,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")

        if recovery_seconds <= 0:
            raise ValueError("recovery_seconds must be greater than 0")

        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def before_request(self) -> None:
        if self._state == CircuitState.CLOSED:
            return

        if self._state == CircuitState.HALF_OPEN:
            raise CircuitBreakerOpenError(0.0)

        if self._opened_at is None:
            self._opened_at = monotonic()

        elapsed = monotonic() - self._opened_at
        remaining = self.recovery_seconds - elapsed

        if remaining > 0:
            raise CircuitBreakerOpenError(remaining)

        self._state = CircuitState.HALF_OPEN

    def record_success(self) -> None:
        self._failure_count = 0
        self._opened_at = None
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._failure_count = self.failure_threshold
            self._opened_at = monotonic()
            self._state = CircuitState.OPEN
            return

        self._failure_count += 1

        if self._failure_count >= self.failure_threshold:
            self._opened_at = monotonic()
            self._state = CircuitState.OPEN
