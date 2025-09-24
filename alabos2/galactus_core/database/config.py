"""Database configuration for alabos."""

from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    postgres_host: str = Field(default="localhost", alias="alabos_POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="alabos_POSTGRES_PORT")
    postgres_database: str = Field(
        default="alabos", alias="alabos_POSTGRES_DATABASE"
    )
    postgres_user: str = Field(default="alabos", alias="alabos_POSTGRES_USER")
    postgres_password: str = Field(
        default="password", alias="alabos_POSTGRES_PASSWORD"
    )
    postgres_schema: str = Field(default="public", alias="alabos_POSTGRES_SCHEMA")

    timescale_hypertable_interval: str = Field(
        default="7 days", alias="alabos_TIMESCALE_INTERVAL"
    )

    pool_size: int = Field(default=20, alias="alabos_POOL_SIZE")
    max_overflow: int = Field(default=30, alias="alabos_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, alias="alabos_POOL_TIMEOUT")
    pool_recycle: int = Field(default=3600, alias="alabos_POOL_RECYCLE")

    kafka_bootstrap_servers: str = Field(
        default="localhost:9092", alias="alabos_KAFKA_BOOTSTRAP_SERVERS"
    )
    kafka_client_id: str = Field(default="alabos", alias="alabos_KAFKA_CLIENT_ID")
    kafka_group_id: str = Field(
        default="alabos_consumers", alias="alabos_KAFKA_GROUP_ID"
    )

    redis_host: str = Field(default="localhost", alias="alabos_REDIS_HOST")
    redis_port: int = Field(default=6379, alias="alabos_REDIS_PORT")
    redis_password: str | None = Field(default=None, alias="alabos_REDIS_PASSWORD")
    redis_database: int = Field(default=0, alias="alabos_REDIS_DATABASE")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "populate_by_name": True,
    }


db_settings = DatabaseSettings()
