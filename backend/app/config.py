"""
Configuration management for PartLogic backend.
Uses pydantic-settings for environment variable handling.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # API Configuration
    api_title: str = "PartLogic API"
    api_version: str = "2.0.0"
    debug: bool = False

    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    cache_ttl_seconds: int = 21600  # 6 hours

    # eBay API Configuration
    ebay_app_id: Optional[str] = None
    ebay_cert_id: Optional[str] = None
    ebay_dev_id: Optional[str] = None
    ebay_sandbox: bool = True  # Use sandbox by default
    ebay_oauth_scope: str = "https://api.ebay.com/oauth/api_scope"

    # Connector Configuration
    connector_timeout: int = 15  # per-connector timeout in seconds
    request_timeout: int = 30
    rate_limit_delay: float = 1.0  # seconds between requests
    max_results_per_source: int = 20

    # Car-Part.com Configuration
    carpart_default_zip: Optional[str] = None


# Global settings instance
settings = Settings()
