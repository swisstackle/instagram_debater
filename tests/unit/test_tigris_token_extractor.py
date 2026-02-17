"""
Unit tests for Tigris token extractor.
"""
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

import pytest

from src.tigris_token_extractor import TigrisTokenExtractor


class TestTigrisTokenExtractor:
    """Test suite for TigrisTokenExtractor."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3/Tigris client."""
        return Mock()

    @pytest.fixture
    def extractor(self, mock_s3_client):
        """Create a TigrisTokenExtractor with mocked S3 client."""
        extractor = TigrisTokenExtractor()
        extractor.s3_client = mock_s3_client
        return extractor

    def test_initialization(self):
        """Test that extractor initializes properly."""
        with patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test_key',
            'AWS_SECRET_ACCESS_KEY': 'test_secret',
            'TIGRIS_BUCKET_NAME': 'test_bucket'
        }):
            extractor = TigrisTokenExtractor()
            assert extractor is not None

    def test_save_token_uploads_to_s3(self, extractor):
        """Test that save_token uploads to S3/Tigris."""
        extractor.save_token("test_token_123", user_id="user_123")
        
        # Verify put_object was called
        extractor.s3_client.put_object.assert_called_once()
        
        # Check call arguments
        call_kwargs = extractor.s3_client.put_object.call_args[1]
        assert 'Body' in call_kwargs
        
        # Verify the uploaded JSON contains the token
        body = call_kwargs['Body']
        if isinstance(body, str):
            data = json.loads(body)
        else:
            data = json.loads(body.decode('utf-8'))
        
        assert data["access_token"] == "test_token_123"
        assert data["user_id"] == "user_123"

    def test_get_token_retrieves_from_s3(self, extractor):
        """Test that get_token retrieves from S3/Tigris."""
        token_data = {
            "access_token": "test_token_123",
            "token_type": "bearer",
            "user_id": "user_456"
        }
        
        mock_response = {'Body': Mock()}
        mock_response['Body'].read.return_value = json.dumps(token_data).encode('utf-8')
        extractor.s3_client.get_object.return_value = mock_response
        
        result = extractor.get_token()
        
        assert result is not None
        assert result["access_token"] == "test_token_123"
        assert result["user_id"] == "user_456"

    def test_get_token_not_found(self, extractor):
        """Test that get_token returns None when object not found."""
        from botocore.exceptions import ClientError
        
        error = ClientError(
            {'Error': {'Code': 'NoSuchKey'}},
            'GetObject'
        )
        extractor.s3_client.get_object.side_effect = error
        
        result = extractor.get_token()
        assert result is None

    def test_get_token_handles_corruption(self, extractor):
        """Test that get_token handles corrupted JSON gracefully."""
        mock_response = {'Body': Mock()}
        mock_response['Body'].read.return_value = b"invalid json"
        extractor.s3_client.get_object.return_value = mock_response
        
        result = extractor.get_token()
        assert result is None

    def test_is_token_expired_no_token(self, extractor):
        """Test that is_token_expired returns True when no token exists."""
        extractor.s3_client.get_object.side_effect = Exception("NotFound")
        
        result = extractor.is_token_expired()
        assert result is True

    def test_is_token_expired_valid_token(self, extractor):
        """Test that is_token_expired returns False for valid token."""
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace("+00:00", "Z")
        token_data = {
            "access_token": "test_token",
            "expires_at": expires_at
        }
        
        mock_response = {'Body': Mock()}
        mock_response['Body'].read.return_value = json.dumps(token_data).encode('utf-8')
        extractor.s3_client.get_object.return_value = mock_response
        
        result = extractor.is_token_expired(buffer_days=5)
        assert result is False

    def test_is_token_expired_expiring_soon(self, extractor):
        """Test that is_token_expired returns True when token expires within buffer."""
        # Token expires in 3 days (within 5 day buffer)
        expires_at = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat().replace("+00:00", "Z")
        token_data = {
            "access_token": "test_token",
            "expires_at": expires_at
        }
        
        mock_response = {'Body': Mock()}
        mock_response['Body'].read.return_value = json.dumps(token_data).encode('utf-8')
        extractor.s3_client.get_object.return_value = mock_response
        
        result = extractor.is_token_expired(buffer_days=5)
        assert result is True

    def test_clear_token_deletes_from_s3(self, extractor):
        """Test that clear_token deletes from S3/Tigris."""
        extractor.clear_token()
        
        extractor.s3_client.delete_object.assert_called_once()

    def test_refresh_token_success(self, extractor, monkeypatch):
        """Test successful token refresh."""
        # Mock existing token
        existing_token = {
            "access_token": "old_token",
            "expires_at": "2026-03-01T00:00:00Z"
        }
        mock_response = {'Body': Mock()}
        mock_response['Body'].read.return_value = json.dumps(existing_token).encode('utf-8')
        extractor.s3_client.get_object.return_value = mock_response
        
        # Mock refresh API
        import requests
        mock_refresh_response = Mock()
        mock_refresh_response.status_code = 200
        mock_refresh_response.json.return_value = {
            "access_token": "new_token",
            "token_type": "bearer",
            "expires_in": 5184000
        }
        
        monkeypatch.setattr(requests, 'get', Mock(return_value=mock_refresh_response))
        
        result = extractor.refresh_token("test_secret")
        
        assert result is True
        # Verify new token was saved
        extractor.s3_client.put_object.assert_called()

    def test_refresh_token_no_existing_token(self, extractor):
        """Test refresh_token returns False when no token exists."""
        extractor.s3_client.get_object.side_effect = Exception("NotFound")
        
        result = extractor.refresh_token("test_secret")
        assert result is False

    def test_refresh_token_api_error(self, extractor, monkeypatch):
        """Test refresh_token handles API errors gracefully."""
        existing_token = {
            "access_token": "old_token",
            "expires_at": "2026-03-01T00:00:00Z"
        }
        mock_response = {'Body': Mock()}
        mock_response['Body'].read.return_value = json.dumps(existing_token).encode('utf-8')
        extractor.s3_client.get_object.return_value = mock_response
        
        import requests
        mock_refresh_response = Mock()
        mock_refresh_response.status_code = 400
        monkeypatch.setattr(requests, 'get', Mock(return_value=mock_refresh_response))
        
        result = extractor.refresh_token("test_secret")
        assert result is False
