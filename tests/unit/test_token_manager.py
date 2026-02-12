"""
Unit tests for token management.
"""
import os
import json
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest
import requests_mock

from src.token_manager import TokenManager


class TestTokenManager:
    """Test suite for TokenManager class."""

    @pytest.fixture
    def temp_state_dir(self):
        """Create a temporary state directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def token_manager(self, temp_state_dir):
        """Create a TokenManager instance with temporary state directory."""
        return TokenManager(state_dir=temp_state_dir)

    def test_token_manager_initialization(self, temp_state_dir):
        """Test that TokenManager initializes properly."""
        manager = TokenManager(state_dir=temp_state_dir)
        assert manager is not None
        assert manager.state_dir == temp_state_dir
        assert manager.token_file == os.path.join(temp_state_dir, "instagram_token.json")

    def test_save_token_creates_file(self, token_manager):
        """Test that save_token creates a token file."""
        token_manager.save_token(
            access_token="test_token_123",
            user_id="12345",
            username="testuser"
        )
        
        assert os.path.exists(token_manager.token_file)

    def test_save_token_correct_format(self, token_manager):
        """Test that save_token stores data in correct JSON format."""
        token_manager.save_token(
            access_token="test_token_123",
            token_type="bearer",
            expires_in=5184000,
            user_id="12345",
            username="testuser"
        )
        
        with open(token_manager.token_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["access_token"] == "test_token_123"
        assert data["token_type"] == "bearer"
        assert "expires_at" in data
        assert data["user_id"] == "12345"
        assert data["username"] == "testuser"

    def test_save_token_expiration_calculation(self, token_manager):
        """Test that save_token calculates expiration correctly."""
        now = datetime.now(timezone.utc)
        token_manager.save_token(
            access_token="test_token_123",
            expires_in=3600  # 1 hour
        )
        
        with open(token_manager.token_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
        expected_expiry = now + timedelta(seconds=3600)
        
        # Allow 5 second tolerance for test execution time
        assert abs((expires_at - expected_expiry).total_seconds()) < 5

    def test_get_token_missing_file(self, token_manager):
        """Test that get_token returns None when file doesn't exist."""
        result = token_manager.get_token()
        assert result is None

    def test_get_token_retrieves_data(self, token_manager):
        """Test that get_token retrieves stored token data."""
        token_manager.save_token(
            access_token="test_token_456",
            user_id="67890",
            username="anotheruser"
        )
        
        token_data = token_manager.get_token()
        
        assert token_data is not None
        assert token_data["access_token"] == "test_token_456"
        assert token_data["user_id"] == "67890"
        assert token_data["username"] == "anotheruser"

    def test_is_token_expired_no_token(self, token_manager):
        """Test that is_token_expired returns True when no token exists."""
        assert token_manager.is_token_expired() is True

    def test_is_token_expired_valid_token(self, token_manager):
        """Test that is_token_expired returns False for valid token."""
        # Token expires in 30 days
        token_manager.save_token(
            access_token="test_token",
            expires_in=30 * 24 * 60 * 60
        )
        
        assert token_manager.is_token_expired() is False

    def test_is_token_expired_within_buffer(self, token_manager):
        """Test that is_token_expired returns True when within buffer period."""
        # Token expires in 3 days, buffer is 5 days
        token_manager.save_token(
            access_token="test_token",
            expires_in=3 * 24 * 60 * 60
        )
        
        assert token_manager.is_token_expired(buffer_days=5) is True

    def test_is_token_expired_already_expired(self, token_manager):
        """Test that is_token_expired returns True for expired token."""
        # Token expired 1 day ago
        token_manager.save_token(
            access_token="test_token",
            expires_in=-1 * 24 * 60 * 60
        )
        
        assert token_manager.is_token_expired() is True

    def test_refresh_token_success(self, token_manager):
        """Test successful token refresh via Instagram API."""
        # Save an initial token
        token_manager.save_token(
            access_token="old_token_123",
            expires_in=10 * 24 * 60 * 60  # 10 days
        )
        
        with requests_mock.Mocker() as m:
            m.get(
                'https://graph.instagram.com/refresh_access_token',
                json={
                    'access_token': 'new_token_456',
                    'token_type': 'bearer',
                    'expires_in': 5184000  # 60 days
                }
            )
            
            result = token_manager.refresh_token(client_secret="test_secret")
            
            assert result is True
            
            # Verify new token was saved
            token_data = token_manager.get_token()
            assert token_data["access_token"] == "new_token_456"

    def test_refresh_token_no_existing_token(self, token_manager):
        """Test that refresh_token fails when no token exists."""
        result = token_manager.refresh_token(client_secret="test_secret")
        assert result is False

    def test_refresh_token_api_error(self, token_manager):
        """Test that refresh_token handles API errors gracefully."""
        token_manager.save_token(
            access_token="old_token_123",
            expires_in=10 * 24 * 60 * 60
        )
        
        with requests_mock.Mocker() as m:
            m.get(
                'https://graph.instagram.com/refresh_access_token',
                status_code=400,
                json={'error': 'Invalid token'}
            )
            
            result = token_manager.refresh_token(client_secret="test_secret")
            assert result is False

    def test_clear_token_removes_file(self, token_manager):
        """Test that clear_token removes the token file."""
        token_manager.save_token(access_token="test_token")
        assert os.path.exists(token_manager.token_file)
        
        token_manager.clear_token()
        assert not os.path.exists(token_manager.token_file)

    def test_clear_token_no_file(self, token_manager):
        """Test that clear_token doesn't fail when file doesn't exist."""
        # Should not raise an exception
        token_manager.clear_token()
        assert not os.path.exists(token_manager.token_file)

    def test_save_token_creates_directory(self):
        """Test that save_token creates state directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_dir = os.path.join(temp_dir, "new_state_dir")
            manager = TokenManager(state_dir=non_existent_dir)
            
            manager.save_token(access_token="test_token")
            
            assert os.path.exists(non_existent_dir)
            assert os.path.exists(manager.token_file)
