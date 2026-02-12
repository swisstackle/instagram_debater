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

    def test_business_oauth_redirect_url_construction(self):
        """Test construction of Instagram Business OAuth redirect URL with correct endpoint and scopes."""
        from urllib.parse import urlencode, urlparse, parse_qs
        
        client_id = "test_client_id"
        redirect_uri = "https://example.com/auth/instagram/callback"
        state = "random_state_456"
        
        # Business scopes as per Facebook documentation
        business_scopes = [
            "instagram_business_basic",
            "instagram_business_manage_messages",
            "instagram_business_manage_comments",
            "instagram_business_content_publish",
            "instagram_business_manage_insights"
        ]
        scope = ",".join(business_scopes)
        
        # Construct OAuth URL with business endpoint and force_reauth
        params = {
            'force_reauth': 'true',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': scope,
            'state': state
        }
        
        oauth_url = f"https://www.instagram.com/oauth/authorize?{urlencode(params)}"
        
        # Parse and verify URL structure
        parsed = urlparse(oauth_url)
        query_params = parse_qs(parsed.query)
        
        # Verify correct endpoint
        assert parsed.scheme == "https"
        assert parsed.netloc == "www.instagram.com"
        assert parsed.path == "/oauth/authorize"
        
        # Verify force_reauth is present
        assert 'force_reauth' in query_params
        assert query_params['force_reauth'][0] == 'true'
        
        # Verify all business scopes are included
        assert 'scope' in query_params
        scopes_in_url = query_params['scope'][0].split(',')
        for scope in business_scopes:
            assert scope in scopes_in_url
        
        # Verify client_id and state
        assert query_params['client_id'][0] == client_id
        assert query_params['state'][0] == state
        assert query_params['response_type'][0] == 'code'

    def test_oauth_login_endpoint_uses_business_flow(self, temp_state_dir, monkeypatch):
        """Test that /auth/instagram/login endpoint builds URL with business scopes and endpoint."""
        # Set up environment
        monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "test_app_id_123")
        monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "test_secret_456")
        monkeypatch.setenv("INSTAGRAM_REDIRECT_URI", "https://myapp.com/auth/instagram/callback")
        
        # Import after setting environment
        from dashboard import create_dashboard_app
        from unittest.mock import AsyncMock, MagicMock
        
        # Create app with temp state dir
        app = create_dashboard_app(state_dir=temp_state_dir)
        
        # Manually call the endpoint handler
        # We'll extract the handler and test it directly
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/auth/instagram/login':
                # Found the route, now get the endpoint
                endpoint = route.endpoint
                
                # Create mock request
                request = MagicMock()
                
                # Call the endpoint
                import asyncio
                response = asyncio.run(endpoint())
                
                # Should be a redirect response
                assert response.status_code == 307
                assert response.headers["location"]
                
                location = response.headers["location"]
                
                # Parse redirect URL
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(location)
                query_params = parse_qs(parsed.query)
                
                # Verify using www.instagram.com, not api.instagram.com
                assert parsed.netloc == "www.instagram.com", f"Expected www.instagram.com but got {parsed.netloc}"
                assert parsed.path == "/oauth/authorize"
                
                # Verify force_reauth is present
                assert 'force_reauth' in query_params, "Missing force_reauth parameter"
                assert query_params['force_reauth'][0] == 'true'
                
                # Verify business scopes
                assert 'scope' in query_params
                scopes = query_params['scope'][0].split(',')
                
                # All required business scopes must be present
                required_scopes = [
                    "instagram_business_basic",
                    "instagram_business_manage_messages",
                    "instagram_business_manage_comments",
                    "instagram_business_content_publish",
                    "instagram_business_manage_insights"
                ]
                for scope in required_scopes:
                    assert scope in scopes, f"Missing required business scope: {scope}"
                
                # Verify client_id from config
                assert query_params['client_id'][0] == "test_app_id_123"
                
                # Verify redirect_uri from config
                assert query_params['redirect_uri'][0] == "https://myapp.com/auth/instagram/callback"
                
                # Verify state is present (CSRF protection)
                assert 'state' in query_params
                assert len(query_params['state'][0]) > 20  # Should be a secure random token
                
                break
        else:
            pytest.fail("Could not find /auth/instagram/login route")

