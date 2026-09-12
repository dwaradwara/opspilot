from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    app_name: str = "OpsPilot"
    environment: str = "development"
    log_level: str = "INFO"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    database_url: str | None = None
    database_host: str | None = None
    database_port: int = 5432
    database_name: str = "opspilot"
    database_user: str | None = None
    database_password: str | None = None
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

    feature_ticket_notifications_enabled: bool = True

    otel_service_name: str = "opspilot-api"
    otel_exporter_otlp_endpoint: str = "http://tempo:4318/v1/traces"
    otel_environment: str = "development"

    @model_validator(mode="after")
    def resolve_database_url(self):
        if self.database_url:
            return self

        if not self.database_host or not self.database_user or not self.database_password:
            raise ValueError(
                "DATABASE_URL or DATABASE_HOST, DATABASE_USER, and DATABASE_PASSWORD are required"
            )

        url = URL.create(
            drivername="postgresql+asyncpg",
            username=self.database_user,
            password=self.database_password,
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        )

        self.database_url = url.render_as_string(hide_password=False)
        return self
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
