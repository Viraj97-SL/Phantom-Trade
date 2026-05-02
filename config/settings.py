"""
config/settings.py
Central configuration — loads from .env via pydantic-settings.
All modules import from here — never import os.environ directly.
"""
from dotenv import load_dotenv
load_dotenv()  # push .env vars into os.environ so boto3/SDK can find them

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── MongoDB ──────────────────────────────────────────────────────────
    mongodb_uri: str = Field(..., description="MongoDB Atlas connection string")
    mongodb_db: str = Field("phantom_trade", description="Database name")

    # ── Voyage AI ────────────────────────────────────────────────────────
    voyage_api_key: str = Field(..., description="Voyage AI API key from Atlas")

    # ── AWS ──────────────────────────────────────────────────────────────
    aws_access_key_id: str = Field("", description="AWS access key")
    aws_secret_access_key: str = Field("", description="AWS secret key")
    aws_default_region: str = Field("us-east-1", description="AWS region")
    s3_bucket: str = Field("phantom-trade-avb", description="S3 bucket name")

    # ── Anthropic (fallback — optional) ─────────────────────────────────
    anthropic_api_key: str = Field("", description="Anthropic API key")

    # ── Gemini (fallback if Bedrock unavailable) ─────────────────────────
    gemini_api_key: str = Field("", description="Google Gemini API key")

    # ── LangSmith ────────────────────────────────────────────────────────
    langchain_tracing_v2: str = Field("true")
    langchain_api_key: str = Field("", description="LangSmith API key")
    langchain_project: str = Field("phantom-trade")
    langchain_endpoint: str = Field("https://api.smith.langchain.com")

    # ── External APIs ────────────────────────────────────────────────────
    x_bearer_token: str = Field("", description="X API v2 Bearer Token")
    brave_api_key: str = Field("", description="Brave Search API key (legacy)")
    tavily_api_key: str = Field("", description="Tavily Search API key (primary news source)")

    # ── App Settings ─────────────────────────────────────────────────────
    app_env: str = Field("development")
    log_level: str = Field("INFO")
    max_retries: int = Field(3)

    # ── Agent Thresholds ─────────────────────────────────────────────────
    alert_threshold: int = Field(15, description="Min risk_delta to trigger advisory")
    critical_threshold: int = Field(80, description="risk_level above which HITL fires")
    similarity_threshold: float = Field(0.75, description="Min cosine sim for RB retrieval")
    decay_rate: float = Field(0.98, description="Daily decay multiplier for RB entries")
    decay_floor: float = Field(0.3, description="Prune RB entries below this score")

    # ── LLM Model IDs ────────────────────────────────────────────────────
    bedrock_sonnet_id: str = Field(
        "anthropic.claude-sonnet-4-5-20251001",
        description="Bedrock Claude Sonnet model ID"
    )
    bedrock_haiku_id: str = Field(
        "anthropic.claude-haiku-4-5-20251001",
        description="Bedrock Claude Haiku model ID"
    )
    anthropic_sonnet_id: str = Field(
        "claude-sonnet-4-5-20251001",
        description="Anthropic direct Claude Sonnet ID"
    )

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton — call get_settings() everywhere."""
    return Settings()


# Convenience alias
settings = get_settings()
