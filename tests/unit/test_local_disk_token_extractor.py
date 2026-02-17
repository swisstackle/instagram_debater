"""
Unit tests for local disk token extractor.
"""
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

import pytest

from src.local_disk_token_extractor import LocalDiskTokenExtractor


class TestLocalDiskTokenExtractor:
    """Test suite for LocalDiskTokenExtractor."""

    @pytest.fixture
    def temp_state_dir(self):
        """Create a temporary state directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def extractor(self, temp_state_dir):
        """Create a LocalDiskTokenExtractor instance."""
        return LocalDiskTokenExtractor(state_dir=temp_state_dir)

    def test_initialization(self, extractor):
        """Test that extractor initializes properly."""
        assert extractor is not None

    def test_save_token_creates_file(self, extractor, temp_state_dir):
        """Test that save_token creates the token file."""
        token_file = os.path.join(temp_state_dir, "instagram_token.json")
        assert not os.path.exists(token_file)
        
        extractor.save_token("test_token_123")
        
        assert os.path.exists(token_file)

    def test_save_token_correct_format(self, extractor, temp_state_dir):
        """Test that saved token has correct JSON format."""
        extractor.save_token("test_token_123", token_type="bearer", expires_in=5184000)
        
        token_file = os.path.join(temp_state_dir, "instagram_token.json")
        with open(token_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["access_token"] == "test_token_123"
        assert data["token_type"] == "bearer"
        assert "expires_at" in data
        assert "saved_at" in data

    def test_save_token_with_user_data(self, extractor, temp_state_dir):
        """Test that save_token includes user_id and username."""
        extractor.save_token("test_token", user_id="user_123", username="testuser")
        
        token_file = os.path.join(temp_state_dir, "instagram_token.json")
        with open(token_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["user_id"] == "user_123"
        assert data["username"] == "testuser"

    def test_get_token_no_file(self, extractor):
        """Test that get_token returns None when no token file exists."""
        result = extractor.get_token()
        assert result is None

    def test_get_token_retrieves_data(self, extractor, temp_state_dir):
        """Test that get_token retrieves saved token data."""
        extractor.save_token("test_token_123", user_id="user_456")
        
        result = extractor.get_token()
        
        assert result is not None
        assert result["access_token"] == "test_token_123"
        assert result["user_id"] == "user_456"

    def test_is_token_expired_no_token(self, extractor):
        """Test that is_token_expired returns True when no token exists."""
        result = extractor.is_token_expired()
        assert result is True

    def test_is_token_expired_valid_token(self, extractor):
        """Test that is_token_expired returns False for valid token."""
        # Token valid for 30 days
        extractor.save_token("test_token", expires_in=2592000)
        
        result = extractor.is_token_expired(buffer_days=5)
        assert result is False

    def test_is_token_expired_expiring_soon(self, extractor):
        """Test that is_token_expired returns True when token expires within buffer."""
        # Token expires in 3 days (within 5 day buffer)
        extractor.save_token("test_token", expires_in=259200)
        
        result = extractor.is_token_expired(buffer_days=5)
        assert result is True

    def test_is_token_expired_already_expired(self, extractor, temp_state_dir):
        """Test that is_token_expired returns True for already expired token."""
        # Manually create an expired token
        expires_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
        token_data = {
            "access_token": "expired_token",
            "token_type": "bearer",
            "expires_at": expires_at
        }
        
        token_file = os.path.join(temp_state_dir, "instagram_token.json")
        os.makedirs(temp_state_dir, exist_ok=True)
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump(token_data, f)
        
        result = extractor.is_token_expired()
        assert result is True

    def test_clear_token_removes_file(self, extractor, temp_state_dir):
        """Test that clear_token removes the token file."""
        extractor.save_token("test_token")
        
        token_file = os.path.join(temp_state_dir, "instagram_token.json")
        assert os.path.exists(token_file)
        
        extractor.clear_token()
        assert not os.path.exists(token_file)

    def test_clear_token_no_file(self, extractor):
        """Test that clear_token handles missing file gracefully."""
        # Should not raise
        extractor.clear_token()

    def test_save_token_creates_directory(self):
        """Test that save_token creates state directory if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = os.path.join(tmpdir, "nonexistent", "state")
            extractor = LocalDiskTokenExtractor(state_dir=state_dir)
            
            extractor.save_token("test_token")
            
            assert os.path.exists(state_dir)

    def test_refresh_token_success(self, extractor, monkeypatch):
        """Test successful token refresh."""
        # Save initial token
        extractor.save_token("old_token", expires_in=86400)  # 1 day
        
        # Mock the refresh endpoint
        import requests
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_refreshed_token",
            "token_type": "bearer",
            "expires_in": 5184000
        }
        
        monkeypatch.setattr(requests, 'get', Mock(return_value=mock_response))
        
        result = extractor.refresh_token("test_secret")
        
        assert result is True
        token_data = extractor.get_token()
        assert token_data["access_token"] == "new_refreshed_token"

    def test_refresh_token_no_existing_token(self, extractor):
        """Test refresh_token returns False when no token exists."""
        result = extractor.refresh_token("test_secret")
        assert result is False

    def test_refresh_token_api_error(self, extractor, monkeypatch):
        """Test refresh_token handles API errors gracefully."""
        extractor.save_token("test_token")
        
        import requests
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid token"}
        
        monkeypatch.setattr(requests, 'get', Mock(return_value=mock_response))
        
        result = extractor.refresh_token("test_secret")
        assert result is False
