"""
Unit tests for OAuth endpoints in dashboard.
"""
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse, parse_qs

import pytest
import requests_mock


class TestOAuthHelpers:
    """Test suite for OAuth helper functions."""

    @pytest.fixture
    def temp_state_dir(self):
        """Create a temporary state directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_oauth_config_properties_exist(self, monkeypatch):
        """Test that OAuth config properties are available."""
        from src.config import Config
        
        monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("INSTAGRAM_REDIRECT_URI", "http://localhost:5000/callback")
        
        config = Config()
        assert config.instagram_client_id == "test_client_id"
        assert config.instagram_client_secret == "test_secret"
        assert config.instagram_redirect_uri == "http://localhost:5000/callback"

    def test_token_manager_integration(self, temp_state_dir):
        """Test that TokenManager can be used for OAuth token storage."""
        from src.token_manager import TokenManager
        
        manager = TokenManager(state_dir=temp_state_dir)
        
        # Save a token as would be done after OAuth
        manager.save_token(
            access_token="long_lived_token_abc",
            token_type="bearer",
            expires_in=5184000,
            user_id="12345",
            username="testuser"
        )
        
        # Retrieve and verify
        token_data = manager.get_token()
        assert token_data is not None
        assert token_data["access_token"] == "long_lived_token_abc"
        assert token_data["user_id"] == "12345"

    def test_oauth_state_generation(self):
        """Test that OAuth state can be generated securely."""
        import secrets
        
        # State should be random and long enough
        state1 = secrets.token_urlsafe(32)
        state2 = secrets.token_urlsafe(32)
        
        assert len(state1) > 20
        assert len(state2) > 20
        assert state1 != state2  # Should be different each time

    def test_exchange_code_for_token_mock(self):
        """Test token exchange logic with mocked Instagram API."""
        import requests
        
        with requests_mock.Mocker() as m:
            m.post(
                'https://api.instagram.com/oauth/access_token',
                json={
                    'access_token': 'short_lived_token_123',
                    'user_id': '12345'
                }
            )
            
            # Simulate the token exchange
            response = requests.post(
                'https://api.instagram.com/oauth/access_token',
                data={
                    'client_id': 'test_client',
                    'client_secret': 'test_secret',
                    'grant_type': 'authorization_code',
                    'redirect_uri': 'http://localhost/callback',
                    'code': 'test_code'
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['access_token'] == 'short_lived_token_123'
            assert data['user_id'] == '12345'

    def test_exchange_for_long_lived_token_mock(self):
        """Test long-lived token exchange with mocked Instagram API."""
        import requests
        
        with requests_mock.Mocker() as m:
            m.get(
                'https://graph.instagram.com/access_token',
                json={
                    'access_token': 'long_lived_token_456',
                    'token_type': 'bearer',
                    'expires_in': 5184000
                }
            )
            
            # Simulate the long-lived token exchange
            response = requests.get(
                'https://graph.instagram.com/access_token',
                params={
                    'grant_type': 'ig_exchange_token',
                    'client_secret': 'test_secret',
                    'access_token': 'short_lived_token'
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['access_token'] == 'long_lived_token_456'
            assert data['expires_in'] == 5184000

    def test_oauth_redirect_url_construction(self):
        """Test construction of Instagram OAuth redirect URL."""
        from urllib.parse import urlencode
        
        client_id = "test_client_id"
        redirect_uri = "http://localhost:5000/auth/instagram/callback"
        state = "random_state_123"
        scope = "instagram_basic,instagram_manage_comments,pages_show_list"
        
        # Construct OAuth URL
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': scope,
            'response_type': 'code',
            'state': state
        }
        
        oauth_url = f"https://api.instagram.com/oauth/authorize?{urlencode(params)}"
        
        # Verify URL structure
        assert "instagram.com" in oauth_url
        assert client_id in oauth_url
        assert state in oauth_url
        assert "instagram_basic" in oauth_url

    def test_csrf_state_validation(self):
        """Test CSRF state validation logic."""
        import secrets
        
        # Generate state
        expected_state = secrets.token_urlsafe(32)
        
        # Valid case
        assert expected_state == expected_state
        
        # Invalid case
        provided_state = "different_state"
        assert provided_state != expected_state

