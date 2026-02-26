"""
Unit tests for configuration management.
"""
# pylint: disable=unused-import
import json
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

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

    def test_auto_post_enabled_property_true(self, monkeypatch, tmp_path):
        """Test auto_post_enabled property when true."""
        from src.local_disk_mode_extractor import LocalDiskModeExtractor
        extractor = LocalDiskModeExtractor(state_dir=str(tmp_path))
        extractor.set_auto_mode(True)
        with patch('src.mode_extractor_factory.create_mode_extractor', return_value=extractor):
            config = Config()
            assert config.auto_post_enabled is True

    def test_auto_post_enabled_property_false(self, monkeypatch, tmp_path):
        """Test auto_post_enabled property when false."""
        from src.local_disk_mode_extractor import LocalDiskModeExtractor
        extractor = LocalDiskModeExtractor(state_dir=str(tmp_path))
        extractor.set_auto_mode(False)
        with patch('src.mode_extractor_factory.create_mode_extractor', return_value=extractor):
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

    def test_dashboard_port_default(self, monkeypatch):
        """Test dashboard_port property with default value."""
        monkeypatch.delenv("DASHBOARD_PORT", raising=False)
        config = Config()
        assert config.dashboard_port == 5000
        assert isinstance(config.dashboard_port, int)

    def test_dashboard_port_custom(self, monkeypatch):
        """Test dashboard_port property with custom value."""
        monkeypatch.setenv("DASHBOARD_PORT", "3000")
        config = Config()
        assert config.dashboard_port == 3000

    def test_dashboard_host_default(self, monkeypatch):
        """Test dashboard_host property with default value."""
        monkeypatch.delenv("DASHBOARD_HOST", raising=False)
        config = Config()
        assert config.dashboard_host == "127.0.0.1"

    def test_dashboard_host_custom(self, monkeypatch):
        """Test dashboard_host property with custom value."""
        monkeypatch.setenv("DASHBOARD_HOST", "0.0.0.0")
        config = Config()
        assert config.dashboard_host == "0.0.0.0"

    def test_webhook_port_default(self, monkeypatch):
        """Test webhook_port property with default value."""
        monkeypatch.delenv("WEBHOOK_PORT", raising=False)
        config = Config()
        assert config.webhook_port == 8000
        assert isinstance(config.webhook_port, int)

    def test_webhook_port_custom(self, monkeypatch):
        """Test webhook_port property with custom value."""
        monkeypatch.setenv("WEBHOOK_PORT", "9000")
        config = Config()
        assert config.webhook_port == 9000

    def test_webhook_host_default(self, monkeypatch):
        """Test webhook_host property with default value."""
        monkeypatch.delenv("WEBHOOK_HOST", raising=False)
        config = Config()
        assert config.webhook_host == "0.0.0.0"

    def test_webhook_host_custom(self, monkeypatch):
        """Test webhook_host property with custom value."""
        monkeypatch.setenv("WEBHOOK_HOST", "127.0.0.1")
        config = Config()
        assert config.webhook_host == "127.0.0.1"

    def test_instagram_client_id_property(self, monkeypatch):
        """Test instagram_client_id property."""
        monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "test_client_id_123")
        config = Config()
        assert config.instagram_client_id == "test_client_id_123"

    def test_instagram_client_id_default(self, monkeypatch):
        """Test instagram_client_id property with default value."""
        monkeypatch.delenv("INSTAGRAM_CLIENT_ID", raising=False)
        config = Config()
        assert config.instagram_client_id == ""

    def test_instagram_client_secret_property(self, monkeypatch):
        """Test instagram_client_secret property."""
        monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "test_client_secret_456")
        config = Config()
        assert config.instagram_client_secret == "test_client_secret_456"

    def test_instagram_client_secret_default(self, monkeypatch):
        """Test instagram_client_secret property with default value."""
        monkeypatch.delenv("INSTAGRAM_CLIENT_SECRET", raising=False)
        config = Config()
        assert config.instagram_client_secret == ""

    def test_instagram_redirect_uri_property(self, monkeypatch):
        """Test instagram_redirect_uri property."""
        monkeypatch.setenv("INSTAGRAM_REDIRECT_URI", "https://example.com/callback")
        config = Config()
        assert config.instagram_redirect_uri == "https://example.com/callback"

    def test_instagram_redirect_uri_default(self, monkeypatch):
        """Test instagram_redirect_uri property with default value."""
        monkeypatch.delenv("INSTAGRAM_REDIRECT_URI", raising=False)
        config = Config()
        assert config.instagram_redirect_uri == "http://127.0.0.1:5000/auth/instagram/callback"

    # OAuth Token Refresh Integration Tests
    def test_instagram_access_token_prefers_oauth_valid(self, monkeypatch, tmp_path):
        """Test that config prefers valid OAuth token from token extractor."""
        # Setup: Create a token file with a valid (non-expired) token
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace("+00:00", "Z")
        token_data = {
            "access_token": "oauth_token_valid",
            "token_type": "bearer",
            "expires_at": expires_at,
            "user_id": "123456"
        }
        
        token_file = state_dir / "instagram_token.json"
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump(token_data, f)
        
        # Setup env var (should be ignored in favor of OAuth)
        monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "env_var_token")
        monkeypatch.setenv("INSTAGRAM_APP_SECRET", "app_secret")
        
        # Patch factory function at source
        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = token_data
            mock_extractor.is_token_expired.return_value = False
            mock_factory.return_value = mock_extractor
            
            config = Config()
            token = config.instagram_access_token
            
            # Should use OAuth token, not env var
            assert token == "oauth_token_valid"
            mock_extractor.get_token.assert_called()
            mock_extractor.is_token_expired.assert_called_with(buffer_days=5)

    def test_instagram_access_token_refreshes_expired_oauth(self, monkeypatch):
        """Test that config refreshes OAuth token when expired."""
        # Setup: Token extractor indicates token is expired
        token_data = {
            "access_token": "old_oauth_token",
            "token_type": "bearer",
            "user_id": "123456"
        }
        
        refreshed_token_data = {
            "access_token": "refreshed_oauth_token",
            "token_type": "bearer",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace("+00:00", "Z")
        }
        
        monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "env_var_token")
        monkeypatch.setenv("INSTAGRAM_APP_SECRET", "test_secret")
        
        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.side_effect = [token_data, refreshed_token_data]
            mock_extractor.is_token_expired.return_value = True
            mock_extractor.refresh_token.return_value = True
            mock_factory.return_value = mock_extractor
            
            config = Config()
            token = config.instagram_access_token
            
            # Should refresh token and return new one
            assert token == "refreshed_oauth_token"
            mock_extractor.refresh_token.assert_called_with("test_secret")

    def test_instagram_access_token_refresh_fails_falls_back_to_env(self, monkeypatch):
        """Test that config falls back to env var if OAuth refresh fails."""
        token_data = {
            "access_token": "expired_oauth_token",
            "token_type": "bearer",
            "user_id": "123456"
        }
        
        monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "env_var_token")
        monkeypatch.setenv("INSTAGRAM_APP_SECRET", "test_secret")
        
        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = token_data
            mock_extractor.is_token_expired.return_value = True
            mock_extractor.refresh_token.return_value = False  # Refresh fails
            mock_factory.return_value = mock_extractor
            
            config = Config()
            token = config.instagram_access_token
            
            # Should fall back to env var when refresh fails
            assert token == "env_var_token"
            mock_extractor.refresh_token.assert_called()

    def test_instagram_access_token_no_oauth_uses_env_var(self, monkeypatch):
        """Test that config uses env var when no OAuth token exists."""
        monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "env_var_token")
        monkeypatch.delenv("INSTAGRAM_APP_SECRET", raising=False)
        
        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = None  # No OAuth token
            mock_factory.return_value = mock_extractor
            
            config = Config()
            token = config.instagram_access_token
            
            # Should use env var when OAuth unavailable
            assert token == "env_var_token"

    def test_instagram_access_token_handles_exception(self, monkeypatch):
        """Test that config handles token extractor exceptions gracefully."""
        monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "env_var_token")
        
        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_factory.side_effect = Exception("Token extractor import failed")
            
            config = Config()
            token = config.instagram_access_token
            
            # Should fall back to env var on exception
            assert token == "env_var_token"

    # instagram_username Tests
    def test_instagram_username_from_oauth_token(self, monkeypatch):
        """Test that instagram_username prefers username stored in OAuth token."""
        token_data = {
            "access_token": "some_token",
            "token_type": "bearer",
            "username": "oauth_bot_account"
        }
        monkeypatch.setenv("INSTAGRAM_USERNAME", "env_bot_account")

        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = token_data
            mock_factory.return_value = mock_extractor

            config = Config()
            username = config.instagram_username

            # Should use OAuth token username, not env var
            assert username == "oauth_bot_account"
            mock_extractor.get_token.assert_called()

    def test_instagram_username_falls_back_to_env_when_no_oauth_token(self, monkeypatch):
        """Test that instagram_username falls back to env var when OAuth token absent."""
        monkeypatch.setenv("INSTAGRAM_USERNAME", "env_bot_account")

        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = None
            mock_factory.return_value = mock_extractor

            config = Config()
            username = config.instagram_username

            assert username == "env_bot_account"

    def test_instagram_username_falls_back_to_env_when_token_has_no_username(self, monkeypatch):
        """Test that instagram_username falls back to env var when token has no username field."""
        token_data = {
            "access_token": "some_token",
            "token_type": "bearer"
            # no 'username' key
        }
        monkeypatch.setenv("INSTAGRAM_USERNAME", "env_bot_account")

        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = token_data
            mock_factory.return_value = mock_extractor

            config = Config()
            username = config.instagram_username

            assert username == "env_bot_account"

    def test_instagram_username_handles_exception_falls_back_to_env(self, monkeypatch):
        """Test that instagram_username handles token extractor exceptions gracefully."""
        monkeypatch.setenv("INSTAGRAM_USERNAME", "env_bot_account")

        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_factory.side_effect = Exception("Token extractor error")

            config = Config()
            username = config.instagram_username

            assert username == "env_bot_account"

    def test_instagram_username_returns_empty_when_no_source(self, monkeypatch):
        """Test that instagram_username returns empty string when no OAuth token and no env var."""
        monkeypatch.delenv("INSTAGRAM_USERNAME", raising=False)

        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = None
            mock_factory.return_value = mock_extractor

            config = Config()
            username = config.instagram_username

            assert username == ""
