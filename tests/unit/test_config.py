"""
Unit tests for configuration management.
"""
# pylint: disable=unused-import
import os

import pytest

from src.config import Config


class TestConfig:
    """Test suite for Config class."""

    def test_config_initialization(self):
        """Test that Config initializes properly."""
        config = Config()
        assert config is not None

    def test_get_with_default(self):
        """Test get method with default value."""
        config = Config()
        value = config.get("NONEXISTENT_KEY", "default_value")
        assert value == "default_value"

    def test_instagram_app_secret_property(self, monkeypatch):
        """Test instagram_app_secret property."""
        monkeypatch.setenv("INSTAGRAM_APP_SECRET", "test_secret")
        config = Config()
        assert config.instagram_app_secret == "test_secret"

    def test_instagram_access_token_property(self, monkeypatch):
        """Test instagram_access_token property."""
        monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "test_token")
        config = Config()
        assert config.instagram_access_token == "test_token"

    def test_instagram_verify_token_property(self, monkeypatch):
        """Test instagram_verify_token property."""
        monkeypatch.setenv("INSTAGRAM_VERIFY_TOKEN", "test_verify")
        config = Config()
        assert config.instagram_verify_token == "test_verify"

    def test_openrouter_api_key_property(self, monkeypatch):
        """Test openrouter_api_key property."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_openrouter_key")
        config = Config()
        assert config.openrouter_api_key == "test_openrouter_key"

    def test_model_name_property(self, monkeypatch):
        """Test model_name property with default."""
        monkeypatch.setenv("MODEL_NAME", "google/gemini-flash-2.0")
        config = Config()
        assert config.model_name == "google/gemini-flash-2.0"

    def test_max_tokens_property(self, monkeypatch):
        """Test max_tokens property returns integer."""
        monkeypatch.setenv("MAX_TOKENS", "2000")
        config = Config()
        assert config.max_tokens == 2000
        assert isinstance(config.max_tokens, int)

    def test_temperature_property(self, monkeypatch):
        """Test temperature property returns float."""
        monkeypatch.setenv("TEMPERATURE", "0.7")
        config = Config()
        assert config.temperature == 0.7
        assert isinstance(config.temperature, float)

    def test_auto_post_enabled_property_true(self, monkeypatch):
        """Test auto_post_enabled property when true."""
        monkeypatch.setenv("AUTO_POST_ENABLED", "true")
        config = Config()
        assert config.auto_post_enabled is True

    def test_auto_post_enabled_property_false(self, monkeypatch):
        """Test auto_post_enabled property when false."""
        monkeypatch.setenv("AUTO_POST_ENABLED", "false")
        config = Config()
        assert config.auto_post_enabled is False

    def test_articles_config_single_article(self, monkeypatch):
        """Test articles_config property with single article (JSON format)."""
        monkeypatch.setenv(
            "ARTICLES_CONFIG",
            '[{"path": "articles/article1.md", "link": "https://example.com/article1"}]'
        )
        config = Config()
        articles = config.articles_config
        assert len(articles) == 1
        assert articles[0]["path"] == "articles/article1.md"
        assert articles[0]["link"] == "https://example.com/article1"

    def test_articles_config_multiple_articles(self, monkeypatch):
        """Test articles_config property with multiple articles."""
        monkeypatch.setenv(
            "ARTICLES_CONFIG",
            '[{"path": "articles/article1.md", "link": "https://example.com/article1"}, '
            '{"path": "articles/article2.md", "link": "https://example.com/article2"}]'
        )
        config = Config()
        articles = config.articles_config
        assert len(articles) == 2
        assert articles[0]["path"] == "articles/article1.md"
        assert articles[1]["path"] == "articles/article2.md"

    def test_articles_config_empty_when_not_set(self, monkeypatch):
        """Test articles_config returns empty list when ARTICLES_CONFIG not set."""
        monkeypatch.delenv("ARTICLES_CONFIG", raising=False)
        config = Config()
        articles = config.articles_config
        assert articles == []
