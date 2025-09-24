"""
Database configuration for Galactus.
"""

import os
from typing import Optional

from pydantic import BaseSettings, Field


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    postgres_host: str = Field(default="localhost", env="GALACTUS_POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="GALACTUS_POSTGRES_PORT")
    postgres_database: str = Field(default="galactus", env="GALACTUS_POSTGRES_DATABASE")
    postgres_user: str = Field(default="galactus", env="GALACTUS_POSTGRES_USER")
    postgres_password: str = Field(default="password", env="GALACTUS_POSTGRES_PASSWORD")
    postgres_schema: str = Field(default="public", env="GALACTUS_POSTGRES_SCHEMA")

    timescale_hypertable_interval: str = Field(default="7 days", env="GALACTUS_TIMESCALE_INTERVAL")

    pool_size: int = Field(default=20, env="GALACTUS_POOL_SIZE")
    max_overflow: int = Field(default=30, env="GALACTUS_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="GALACTUS_POOL_TIMEOUT")
    pool_recycle: int = Field(default=3600, env="GALACTUS_POOL_RECYCLE")

    kafka_bootstrap_servers: str = Field(default="localhost:9092", env="GALACTUS_KAFKA_BOOTSTRAP_SERVERS")
    kafka_client_id: str = Field(default="galactus", env="GALACTUS_KAFKA_CLIENT_ID")
    kafka_group_id: str = Field(default="galactus_consumers", env="GALACTUS_KAFKA_GROUP_ID")

    redis_host: str = Field(default="localhost", env="GALACTUS_REDIS_HOST")
    redis_port: int = Field(default=6379, env="GALACTUS_REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="GALACTUS_REDIS_PASSWORD")
    redis_database: int = Field(default=0, env="GALACTUS_REDIS_DATABASE")

    class Config:
        env_file = ".env"
        case_sensitive = False


db_settings = DatabaseSettings()
