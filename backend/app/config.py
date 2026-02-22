"""
Configuration management for PartLogic backend.
Uses pydantic-settings for environment variable handling.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    # API Configuration
    api_title: str = "PartLogic API"
    api_version: str = "2.0.0"
    debug: bool = False

    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    cache_ttl_seconds: int = 21600  # 6 hours
    cache_ttl_degraded_seconds: int = 300  # 5 minutes for results missing AI or listings

    # eBay API Configuration
    ebay_app_id: str | None = None
    ebay_cert_id: str | None = None
    ebay_dev_id: str | None = None
    ebay_sandbox: bool = True  # Use sandbox by default
    ebay_oauth_scope: str = "https://api.ebay.com/oauth/api_scope"

    # Connector Configuration
    connector_timeout: int = 15  # per-connector timeout in seconds
    request_timeout: int = 30
    rate_limit_delay: float = 1.0  # seconds between requests
    max_results_per_source: int = 20

    # Scraping Configuration
    scrape_enabled: bool = True  # Global kill switch; false = all connectors use link generation
    playwright_enabled: bool = True  # Disable if Chromium not installed

    # Car-Part.com Configuration
    carpart_default_zip: str | None = None

    # Interchange Configuration
    interchange_enabled: bool = True
    max_interchange_searches: int = 3

    # Community & AI Synthesis Configuration
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str = "PartLogic/1.0"
    community_enabled: bool = True
    ai_synthesis_enabled: bool = True
    community_cache_ttl: int = 604800  # 7 days

    # AI Provider Configuration
    # Priority: Gemini (free) > OpenAI (cheapest paid) > Anthropic. Set whichever key you have.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"  # Free tier: 500 RPD, great for structured JSON
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-nano"  # Cheapest paid: ~$0.001/query
    anthropic_api_key: str | None = None


# Global settings instance
settings = Settings()
