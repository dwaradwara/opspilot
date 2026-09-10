from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OpsPilot"
    environment: str = "development"
    log_level: str = "INFO"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    database_url: str
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout_seconds: float = 30.0

    redis_url: str
    redis_queue_key: str = "opspilot:jobs"
    redis_operation_timeout_seconds: float = 2.0
    redis_retry_attempts: int = 3
    redis_retry_base_delay_seconds: float = 0.5
    redis_retry_max_delay_seconds: float = 2.0
    redis_circuit_failure_threshold: int = 3
    redis_circuit_recovery_seconds: float = 10.0

    rate_limit_enabled: bool = True
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    otel_service_name: str = "opspilot-api"
    otel_exporter_otlp_endpoint: str = "http://tempo:4318/v1/traces"
    otel_environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
