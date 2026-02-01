"""
Configuration management for the Instagram Debate Bot.
Loads environment variables and provides access to configuration settings.
"""
import os
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Configuration settings loaded from environment variables."""

    def __init__(self):
        """Initialize configuration by loading environment variables."""
        load_dotenv()
        self._config = {}

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a configuration value by key.

        Args:
            key: Configuration key name
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return os.getenv(key, default)

    @property
    def instagram_app_secret(self) -> str:
        """Get Instagram app secret."""
        return os.getenv("INSTAGRAM_APP_SECRET", "")

    @property
    def instagram_access_token(self) -> str:
        """Get Instagram access token."""
        return os.getenv("INSTAGRAM_ACCESS_TOKEN", "")

    @property
    def instagram_verify_token(self) -> str:
        """Get Instagram verify token."""
        return os.getenv("INSTAGRAM_VERIFY_TOKEN", "")

    @property
    def openrouter_api_key(self) -> str:
        """Get OpenRouter API key."""
        return os.getenv("OPENROUTER_API_KEY", "")

    @property
    def model_name(self) -> str:
        """Get LLM model name."""
        return os.getenv("MODEL_NAME", "google/gemini-flash-2.0")

    @property
    def max_tokens(self) -> int:
        """Get max tokens for LLM."""
        return int(os.getenv("MAX_TOKENS", "2000"))

    @property
    def temperature(self) -> float:
        """Get temperature for LLM."""
        return float(os.getenv("TEMPERATURE", "0.7"))

    @property
    def auto_post_enabled(self) -> bool:
        """Check if auto-posting is enabled."""
        value = os.getenv("AUTO_POST_ENABLED", "false").lower()
        return value in ["true", "1", "yes"]

    @property
    def article_path(self) -> str:
        """Get path to the article file."""
        return os.getenv("ARTICLE_PATH", "articles/sample_article.md")

    @property
    def article_link(self) -> str:
        """Get link to the online article."""
        return os.getenv("ARTICLE_LINK", "")
