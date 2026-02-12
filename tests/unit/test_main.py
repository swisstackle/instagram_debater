"""
Unit tests for main.py entry point.
"""
import tempfile
import os
from unittest.mock import Mock, patch, call

import pytest

from main import main


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

    @pytest.fixture
    def sample_article(self):
        """Sample article content."""
        return """# Test Article

## §1. Introduction

This is a test article.
"""

    def test_main_single_article(self, mock_config, sample_article):
        """Test main function with single article configuration."""
        with patch("main.Config", return_value=mock_config):
            with patch("main.InstagramAPI") as mock_instagram_api:
                with patch("main.LLMClient") as mock_llm_client:
                    with patch("main.ResponseValidator") as mock_validator:
                        with patch("main.CommentProcessor") as mock_processor:
                            with patch("builtins.open", create=True) as mock_open_file:
                                # Mock file reading
                                mock_open_file.return_value.__enter__.return_value.read.return_value = sample_article

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

                                # Verify article file was opened
                                mock_open_file.assert_called_once_with(
                                    "articles/article1.md", 'r', encoding='utf-8'
                                )

                                # Verify ResponseValidator was created with article text
                                mock_validator.assert_called_once_with(sample_article)

                                # Verify CommentProcessor was initialized
                                mock_processor.assert_called_once()

                                # Verify processor.run() was called
                                mock_processor.return_value.run.assert_called_once()

    def test_main_multiple_articles(self, mock_config, sample_article):
        """Test main function with multiple articles configuration."""
        mock_config.articles_config = [
            {"path": "articles/article1.md", "link": "https://example.com/article1"},
            {"path": "articles/article2.md", "link": "https://example.com/article2"}
        ]

        with patch("main.Config", return_value=mock_config):
            with patch("main.InstagramAPI") as mock_instagram_api:
                with patch("main.LLMClient") as mock_llm_client:
                    with patch("main.ResponseValidator"):
                        with patch("main.CommentProcessor") as mock_processor:
                            with patch("builtins.open", create=True) as mock_open_file:
                                # Mock file reading
                                mock_open_file.return_value.__enter__.return_value.read.return_value = sample_article

                                # Call main
                                main()

                                # Verify InstagramAPI was initialized
                                mock_instagram_api.assert_called_once()

                                # Verify LLMClient was initialized
                                mock_llm_client.assert_called_once()

                                # When multiple articles, should NOT open file in main
                                # (processor will handle this)
                                mock_open_file.assert_not_called()

                                # Verify CommentProcessor was initialized
                                mock_processor.assert_called_once()

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
