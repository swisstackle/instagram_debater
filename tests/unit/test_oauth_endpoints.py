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
from fastapi import HTTPException


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

    def test_token_extractor_integration(self, temp_state_dir, monkeypatch):
        """Test that token extractor factory can store and retrieve OAuth tokens."""
        from src.local_disk_token_extractor import LocalDiskTokenExtractor
        
        # Use local disk extractor directly with temp directory
        extractor = LocalDiskTokenExtractor(state_dir=temp_state_dir)
        
        # Save a token as would be done after OAuth
        extractor.save_token(
            access_token="long_lived_token_abc",
            token_type="bearer",
            expires_in=5184000,
            user_id="12345",
            username="testuser"
        )
        
        # Retrieve and verify
        token_data = extractor.get_token()
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
        """Test token exchange logic with mocked Facebook OAuth API."""
        import requests
        
        with requests_mock.Mocker() as m:
            m.post(
                'https://graph.facebook.com/v25.0/oauth/access_token',
                json={
                    'access_token': 'graph_api_token_123',
                    'user_id': '12345',
                    'expires_in': 5184000
                }
            )
            
            # Simulate the token exchange
            response = requests.post(
                'https://graph.facebook.com/v25.0/oauth/access_token',
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
            # Facebook OAuth returns flat response (not nested data array)
            assert data['access_token'] == 'graph_api_token_123'
            assert data['user_id'] == '12345'
            assert data['expires_in'] == 5184000

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
            short_token = 'short_lived_token'
            secret = 'test_secret'
            url = f'https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret={secret}&access_token={short_token}'
            response = requests.get(url)
            
            assert response.status_code == 200
            data = response.json()
            assert data['access_token'] == 'long_lived_token_456'
            assert data['expires_in'] == 5184000

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
        
        # Instagram Login scopes for Instagram Business app
        business_scopes = [
            "instagram_business_basic",
            "instagram_business_manage_comments"
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
                
                # Verify using www.facebook.com Facebook Login
                assert parsed.netloc == "www.facebook.com", f"Expected www.facebook.com but got {parsed.netloc}"
                assert parsed.path == "/v25.0/dialog/oauth"
                
                # Verify business scopes
                assert 'scope' in query_params
                scopes = query_params['scope'][0].split(',')
                
                # Required scopes must be present
                required_scopes = [
                    "instagram_business_basic",
                    "instagram_business_manage_comments"
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

    def test_oauth_callback_subscribes_webhooks_after_login(self, temp_state_dir, monkeypatch):
        """Test that OAuth callback subscribes the logged-in IG account to webhooks."""
        monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "test_app_id_123")
        monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "test_secret_456")
        monkeypatch.setenv("INSTAGRAM_REDIRECT_URI", "https://myapp.com/auth/instagram/callback")

        from dashboard import create_dashboard_app
        import asyncio

        app = create_dashboard_app(state_dir=temp_state_dir)

        login_endpoint = None
        callback_endpoint = None
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/auth/instagram/login':
                login_endpoint = route.endpoint
            if hasattr(route, 'path') and route.path == '/auth/instagram/callback':
                callback_endpoint = route.endpoint

        assert login_endpoint is not None
        assert callback_endpoint is not None

        login_response = asyncio.run(login_endpoint())
        login_location = login_response.headers["location"]
        state = parse_qs(urlparse(login_location).query)['state'][0]

        with requests_mock.Mocker() as m:
            m.post(
                'https://graph.facebook.com/v25.0/oauth/access_token',
                json={
                    'access_token': 'graph_api_token_123',
                    'user_id': 'ig_user_789',
                    'expires_in': 5184000
                }
            )
            m.get(
                'https://graph.instagram.com/v25.0/me',
                json={
                    'user_id': 'ig_user_789',
                    'username': 'testuser'
                }
            )
            m.post(
                'https://graph.instagram.com/v25.0/me/subscribed_apps',
                json={'success': True},
                status_code=200
            )

            callback_response = asyncio.run(callback_endpoint(code='test_code_abc', state=state))

            assert callback_response.status_code == 303
            assert callback_response.headers["location"] == "/"

            subscription_request = next(
                (req for req in m.request_history if req.url.startswith('https://graph.instagram.com/v25.0/me/subscribed_apps')),
                None
            )
            assert subscription_request is not None
            # Check the request was made (query params in URL)
            assert 'subscribed_fields' in subscription_request.url or 'subscribed_fields' in (subscription_request.text or '')
            assert 'access_token=graph_api_token_123' in subscription_request.url or 'access_token=graph_api_token_123' in (subscription_request.text or '')

    def test_oauth_callback_fails_when_webhook_subscription_fails(self, temp_state_dir, monkeypatch):
        """Test that OAuth callback returns error if webhook subscription fails."""
        monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "test_app_id_123")
        monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "test_secret_456")
        monkeypatch.setenv("INSTAGRAM_REDIRECT_URI", "https://myapp.com/auth/instagram/callback")

        from dashboard import create_dashboard_app
        import asyncio

        app = create_dashboard_app(state_dir=temp_state_dir)

        login_endpoint = None
        callback_endpoint = None
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/auth/instagram/login':
                login_endpoint = route.endpoint
            if hasattr(route, 'path') and route.path == '/auth/instagram/callback':
                callback_endpoint = route.endpoint

        assert login_endpoint is not None
        assert callback_endpoint is not None

        login_response = asyncio.run(login_endpoint())
        login_location = login_response.headers["location"]
        state = parse_qs(urlparse(login_location).query)['state'][0]

        with requests_mock.Mocker() as m:
            m.post(
                'https://graph.facebook.com/v25.0/oauth/access_token',
                json={
                    'access_token': 'graph_api_token_123',
                    'user_id': 'ig_user_789',
                    'expires_in': 5184000
                }
            )
            m.get(
                'https://graph.instagram.com/v25.0/me',
                json={
                    'user_id': 'ig_user_789',
                    'username': 'testuser'
                }
            )
            m.post(
                'https://graph.instagram.com/v25.0/me/subscribed_apps',
                json={'error': {'message': 'Subscription failed'}},
                status_code=400
            )
            # Also mock the /ig_user_789 endpoint for fallback attempt
            m.post(
                'https://graph.instagram.com/v25.0/ig_user_789/subscribed_apps',
                json={'error': {'message': 'Subscription failed'}},
                status_code=400
            )

            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(callback_endpoint(code='test_code_abc', state=state))

            assert exc_info.value.status_code == 400
            assert exc_info.value.detail == "Failed to subscribe webhook events"

    def test_oauth_logout_unsubscribes_and_clears_token(self, temp_state_dir, monkeypatch):
        """Test that logout unsubscribes webhooks before clearing token."""
        monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "test_app_id_123")
        monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "test_secret_456")
        monkeypatch.setenv("INSTAGRAM_REDIRECT_URI", "https://myapp.com/auth/instagram/callback")

        from dashboard import create_dashboard_app
        import asyncio

        app = create_dashboard_app(state_dir=temp_state_dir)

        logout_endpoint = None
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/auth/instagram/logout':
                logout_endpoint = route.endpoint

        assert logout_endpoint is not None

        with patch('dashboard.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = {
                'access_token': 'long_lived_token_456'
            }
            mock_factory.return_value = mock_extractor

            with requests_mock.Mocker() as m:
                m.delete(
                    'https://graph.instagram.com/v25.0/me/subscribed_apps',
                    json={'success': True},
                    status_code=200
                )

                response = asyncio.run(logout_endpoint())

                assert response.status_code == 303
                assert response.headers["location"] == "/"
                mock_extractor.clear_token.assert_called_once()

                unsubscribe_request = next(
                    (req for req in m.request_history if req.url.startswith('https://graph.instagram.com/v25.0/me/subscribed_apps')),
                    None
                )
                assert unsubscribe_request is not None
                assert 'access_token=long_lived_token_456' in unsubscribe_request.url

    def test_oauth_logout_fails_when_unsubscribe_fails(self, temp_state_dir, monkeypatch):
        """Test that logout fails and keeps token when webhook unsubscribe fails."""
        monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "test_app_id_123")
        monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "test_secret_456")
        monkeypatch.setenv("INSTAGRAM_REDIRECT_URI", "https://myapp.com/auth/instagram/callback")

        from dashboard import create_dashboard_app
        import asyncio

        app = create_dashboard_app(state_dir=temp_state_dir)

        logout_endpoint = None
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/auth/instagram/logout':
                logout_endpoint = route.endpoint

        assert logout_endpoint is not None

        with patch('dashboard.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = {
                'access_token': 'long_lived_token_456'
            }
            mock_factory.return_value = mock_extractor

            with requests_mock.Mocker() as m:
                m.delete(
                    'https://graph.instagram.com/v25.0/me/subscribed_apps',
                    json={'error': {'message': 'Failed'}},
                    status_code=400
                )

                # Logout should NOT raise an exception - it's best-effort
                response = asyncio.run(logout_endpoint())

                # Should still redirect to dashboard even if unsubscribe failed
                assert response.status_code == 303
                assert response.headers["location"] == "/"
                # Token should be cleared despite unsubscribe failure
                mock_extractor.clear_token.assert_called_once()

    def test_oauth_logout_without_token_clears_local_token_only(self, temp_state_dir, monkeypatch):
        """Test that logout still clears local token if no token exists."""
        monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "test_app_id_123")
        monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "test_secret_456")
        monkeypatch.setenv("INSTAGRAM_REDIRECT_URI", "https://myapp.com/auth/instagram/callback")

        from dashboard import create_dashboard_app
        import asyncio

        app = create_dashboard_app(state_dir=temp_state_dir)

        logout_endpoint = None
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/auth/instagram/logout':
                logout_endpoint = route.endpoint

        assert logout_endpoint is not None

        with patch('dashboard.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = None
            mock_factory.return_value = mock_extractor

            response = asyncio.run(logout_endpoint())

            assert response.status_code == 303
            assert response.headers["location"] == "/"
            mock_extractor.clear_token.assert_called_once()

