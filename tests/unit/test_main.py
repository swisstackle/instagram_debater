"""
Unit tests for main.py entry point.
"""
import tempfile
import os
from unittest.mock import Mock, patch, call

import pytest

from main import main


@pytest.fixture
def sample_article():
    """Sample article content."""
    return """# Test Article

## §1. Introduction

This is a test article.
"""


class TestMain:
    """Test suite for main function."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        mock_cfg = Mock()
        mock_cfg.instagram_access_token = "test_access_token"
        mock_cfg.instagram_app_secret = "test_app_secret"
        mock_cfg.openrouter_api_key = "test_api_key"
        mock_cfg.model_name = "test_model"
        mock_cfg.max_tokens = 2000
        mock_cfg.temperature = 0.7
        mock_cfg.articles_config = [
            {"path": "articles/article1.md", "link": "https://example.com/article1"}
        ]
        return mock_cfg

    def test_main_single_article(self, mock_config):
        """Test main function with single article configuration."""
        with patch("main.Config", return_value=mock_config):
            with patch("main.InstagramAPI") as mock_instagram_api:
                with patch("main.LLMClient") as mock_llm_client:
                    with patch("main.CommentProcessor") as mock_processor:
                        # Call main
                        main()

                        # Verify InstagramAPI was initialized correctly
                        mock_instagram_api.assert_called_once_with(
                            access_token="test_access_token",
                            app_secret="test_app_secret"
                        )

                        # Verify LLMClient was initialized correctly
                        mock_llm_client.assert_called_once_with(
                            api_key="test_api_key",
                            model_name="test_model",
                            max_tokens=2000,
                            temperature=0.7
                        )

                        # Verify CommentProcessor was initialized with validator=None
                        call_kwargs = mock_processor.call_args[1]
                        assert call_kwargs["validator"] is None

                        # Verify processor.run() was called
                        mock_processor.return_value.run.assert_called_once()

    def test_main_multiple_articles(self, mock_config):
        """Test main function with multiple articles configuration."""
        mock_config.articles_config = [
            {"path": "articles/article1.md", "link": "https://example.com/article1"},
            {"path": "articles/article2.md", "link": "https://example.com/article2"}
        ]

        with patch("main.Config", return_value=mock_config):
            with patch("main.InstagramAPI") as mock_instagram_api:
                with patch("main.LLMClient") as mock_llm_client:
                    with patch("main.CommentProcessor") as mock_processor:
                        # Call main
                        main()

                        # Verify InstagramAPI was initialized
                        mock_instagram_api.assert_called_once()

                        # Verify LLMClient was initialized
                        mock_llm_client.assert_called_once()

                        # Verify CommentProcessor was initialized with validator=None
                        call_kwargs = mock_processor.call_args[1]
                        assert call_kwargs["validator"] is None

                        # Verify processor.run() was called
                        mock_processor.return_value.run.assert_called_once()

    def test_main_no_articles(self, mock_config):
        """Test main function with no articles configured."""
        mock_config.articles_config = []

        with patch("main.Config", return_value=mock_config):
            with patch("main.InstagramAPI"):
                with patch("main.LLMClient"):
                    with patch("main.CommentProcessor") as mock_processor:
                        # Call main
                        main()

                        # Verify processor was still initialized
                        mock_processor.assert_called_once()

                        # Verify processor.run() was called
                        mock_processor.return_value.run.assert_called_once()


class TestMainIntegration:
    """Integration tests for main function with multi-article support."""

    @pytest.fixture
    def mock_config_multi(self):
        """Create a mock config with multiple articles."""
        mock_cfg = Mock()
        mock_cfg.instagram_access_token = "test_token"
        mock_cfg.instagram_app_secret = "test_secret"
        mock_cfg.openrouter_api_key = "test_api_key"
        mock_cfg.model_name = "test_model"
        mock_cfg.max_tokens = 2000
        mock_cfg.temperature = 0.7
        mock_cfg.articles_config = [
            {"path": "articles/fitness.md", "link": "https://example.com/fitness"},
            {"path": "articles/nutrition.md", "link": "https://example.com/nutrition"}
        ]
        return mock_cfg

    def test_integration_multi_article_processor_receives_none_validator(self, mock_config_multi):
        """Test that processor receives None validator in multi-article mode."""
        with patch("main.Config", return_value=mock_config_multi):
            with patch("main.InstagramAPI") as mock_api:
                with patch("main.LLMClient") as mock_llm:
                    with patch("main.CommentProcessor") as mock_processor:
                        # Call main
                        main()

                        # Verify processor was called with validator=None
                        call_kwargs = mock_processor.call_args[1]
                        assert call_kwargs["instagram_api"] == mock_api.return_value
                        assert call_kwargs["llm_client"] == mock_llm.return_value
                        assert call_kwargs["validator"] is None
                        assert call_kwargs["config"] == mock_config_multi

    def test_integration_single_article_processor_receives_none_validator(self):
        """Test that processor receives None validator in single-article mode."""
        mock_cfg = Mock()
        mock_cfg.instagram_access_token = "test_token"
        mock_cfg.instagram_app_secret = "test_secret"
        mock_cfg.openrouter_api_key = "test_api_key"
        mock_cfg.model_name = "test_model"
        mock_cfg.max_tokens = 2000
        mock_cfg.temperature = 0.7
        mock_cfg.articles_config = [
            {"path": "articles/single.md", "link": "https://example.com/single"}
        ]

        with patch("main.Config", return_value=mock_cfg):
            with patch("main.InstagramAPI") as mock_api:
                with patch("main.LLMClient") as mock_llm:
                    with patch("main.CommentProcessor") as mock_processor:
                        # Call main
                        main()

                        # Verify processor was called with validator=None (no backward compatibility)
                        call_kwargs = mock_processor.call_args[1]
                        assert call_kwargs["instagram_api"] == mock_api.return_value
                        assert call_kwargs["llm_client"] == mock_llm.return_value
                        assert call_kwargs["validator"] is None
                        assert call_kwargs["config"] == mock_cfg
