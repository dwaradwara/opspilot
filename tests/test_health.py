from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


def _mock_postgres(
    monkeypatch,
    health,
    *,
    available=True,
    revision=None,
):
    fake_session = AsyncMock()

    if available:
        fake_session.execute = AsyncMock(return_value=None)
        fake_session.scalar = AsyncMock(
            return_value=(
                revision
                if revision is not None
                else health.settings.required_db_schema_revision
            )
        )
    else:
        fake_session.execute = AsyncMock(
            side_effect=RuntimeError("postgres unavailable")
        )

    context = AsyncMock()
    context.__aenter__.return_value = fake_session
    context.__aexit__.return_value = None

    monkeypatch.setattr(
        health,
        "AsyncSessionLocal",
        lambda: context,
    )


def _mock_redis(
    monkeypatch,
    health,
    *,
    available=True,
):
    fake_redis = AsyncMock()

    if available:
        fake_redis.ping = AsyncMock(return_value=True)
    else:
        fake_redis.ping = AsyncMock(
            side_effect=TimeoutError()
        )

    fake_redis.aclose = AsyncMock()

    monkeypatch.setattr(
        health.Redis,
        "from_url",
        lambda *args, **kwargs: fake_redis,
    )


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.headers.get("X-Request-ID")


def test_ready_when_all_dependencies_and_schema_are_valid(
    client: TestClient,
    monkeypatch,
) -> None:
    from app.api.routes import health

    _mock_postgres(monkeypatch, health)
    _mock_redis(monkeypatch, health)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {
            "postgres": True,
            "schema": True,
            "redis": True,
        },
        "degraded_dependencies": [],
    }


def test_ready_is_degraded_when_redis_is_unavailable(
    client: TestClient,
    monkeypatch,
) -> None:
    from app.api.routes import health

    _mock_postgres(monkeypatch, health)
    _mock_redis(
        monkeypatch,
        health,
        available=False,
    )

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"] == {
        "postgres": True,
        "schema": True,
        "redis": False,
    }


def test_ready_returns_503_when_postgres_is_unavailable(
    client: TestClient,
    monkeypatch,
) -> None:
    from app.api.routes import health

    _mock_postgres(
        monkeypatch,
        health,
        available=False,
    )
    _mock_redis(monkeypatch, health)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"] == {
        "postgres": False,
        "schema": False,
        "redis": True,
    }


def test_ready_returns_503_when_schema_is_stale(
    client: TestClient,
    monkeypatch,
) -> None:
    from app.api.routes import health

    _mock_postgres(
        monkeypatch,
        health,
        revision="0003",
    )
    _mock_redis(monkeypatch, health)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"] == {
        "postgres": True,
        "schema": False,
        "redis": True,
    }
