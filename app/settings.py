from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    ...
    max_request_bytes: int = Field(default=1024 * 1024, alias="MAX_REQUEST_BYTES")
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = Field(default="dev-key", alias="API_KEY")
    sqlite_path: str = Field(default="./orchestrator.sqlite", alias="SQLITE_PATH")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    queue_name: str = Field(default="dto:queue", alias="QUEUE_NAME")

    scheduler_interval_seconds: float = Field(default=1.0, alias="SCHEDULER_INTERVAL_SECONDS")

    default_max_attempts: int = Field(default=5, alias="DEFAULT_MAX_ATTEMPTS")
    worker_poll_timeout_seconds: int = Field(default=2, alias="WORKER_POLL_TIMEOUT_SECONDS")
    task_lock_ttl_seconds: int = Field(default=30, alias="TASK_LOCK_TTL_SECONDS")

    retry_base_seconds: float = Field(default=1.0, alias="RETRY_BASE_SECONDS")
    retry_max_seconds: float = Field(default=60.0, alias="RETRY_MAX_SECONDS")
    retry_jitter_seconds: float = Field(default=0.25, alias="RETRY_JITTER_SECONDS")


settings = Settings()