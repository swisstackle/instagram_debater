"""
Configuration management for the Instagram Debate Bot.
Loads environment variables and provides access to configuration settings.
"""
import json
import os
from typing import List, Dict, Optional
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
    def articles_config(self) -> List[Dict[str, str]]:
        """
        Get articles configuration (supports multiple articles).

        Returns list of dicts with 'path' and 'link' keys.
        Returns empty list if JSON parsing fails or ARTICLES_CONFIG not set.
        """
        articles_json = os.getenv("ARTICLES_CONFIG")

        if articles_json:
            try:
                return json.loads(articles_json)
            except json.JSONDecodeError:
                return []

        return []

    @property
    def article_path(self) -> str:
        """
        Get article path (backward compatibility).

        Returns the path of the first article from articles_config.
        Returns empty string if no articles configured.
        """
        articles = self.articles_config
        if articles:
            return articles[0].get("path", "")
        return ""

    @property
    def dashboard_port(self) -> int:
        """Get dashboard server port."""
        return int(os.getenv("DASHBOARD_PORT", "5000"))

    @property
    def dashboard_host(self) -> str:
        """Get dashboard server host."""
        return os.getenv("DASHBOARD_HOST", "127.0.0.1")

    @property
    def webhook_port(self) -> int:
        """Get webhook server port."""
        return int(os.getenv("WEBHOOK_PORT", "8000"))

    @property
    def webhook_host(self) -> str:
        """Get webhook server host."""
        return os.getenv("WEBHOOK_HOST", "0.0.0.0")

    @property
    def instagram_client_id(self) -> str:
        """Get Instagram OAuth client ID (Facebook App ID)."""
        return os.getenv("INSTAGRAM_CLIENT_ID", "")

    @property
    def instagram_client_secret(self) -> str:
        """Get Instagram OAuth client secret (Facebook App Secret)."""
        return os.getenv("INSTAGRAM_CLIENT_SECRET", "")

    @property
    def instagram_redirect_uri(self) -> str:
        """Get Instagram OAuth redirect URI."""
        return os.getenv("INSTAGRAM_REDIRECT_URI", "http://127.0.0.1:5000/auth/instagram/callback")
