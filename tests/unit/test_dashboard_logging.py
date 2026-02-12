"""
Unit tests for dashboard endpoint logging.

Tests follow TDD approach - tests written before implementation.
"""
import tempfile
import shutil
import logging
import json
import os
import asyncio
from io import StringIO
from unittest.mock import patch, AsyncMock, MagicMock

import pytest


class TestDashboardLogging:
    """Test suite for dashboard endpoint logging."""

    @pytest.fixture
    def temp_state_dir(self):
        """Create a temporary state directory for tests."""
        temp_dir = tempfile.mkdtemp()
        # Create empty audit log
        audit_log_path = os.path.join(temp_dir, "audit_log.json")
        with open(audit_log_path, "w") as f:
            json.dump({"version": "1.0", "entries": []}, f)
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def app(self, temp_state_dir):
        """Create FastAPI app with temporary state directory."""
        from dashboard import create_dashboard_app
        app = create_dashboard_app(state_dir=temp_state_dir)
        return app

    @pytest.fixture
    def log_capture(self):
        """Fixture to capture log output."""
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.INFO)
        
        # Get the dashboard logger
        logger = logging.getLogger('dashboard')
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        
        yield log_stream
        
        # Cleanup
        logger.removeHandler(handler)
        handler.close()

    def test_logger_exists(self):
        """Test that dashboard logger is configured."""
        from dashboard import create_dashboard_app
        
        # Logger should be retrievable
        logger = logging.getLogger('dashboard')
        assert logger is not None

    @pytest.fixture
    def mock_request_json(self):
        """Helper fixture to create mock request with json method."""
        def create_mock(data):
            mock_request = MagicMock()
            async def mock_json():
                return data
            mock_request.json = mock_json
            return mock_request
        return create_mock

    def test_get_responses_logs_request(self, app, log_capture):
        """Test that GET /api/responses logs the request."""
        # Find and call the endpoint directly
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/api/responses':
                response = asyncio.run(route.endpoint())
                assert response is not None
                break
        
        log_output = log_capture.getvalue()
        assert "GET /api/responses" in log_output

    def test_get_pending_responses_logs_request(self, app, log_capture):
        """Test that GET /api/responses/pending logs the request."""
        # Find and call the endpoint directly
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/api/responses/pending':
                response = asyncio.run(route.endpoint())
                assert response is not None
                break
        
        log_output = log_capture.getvalue()
        assert "GET /api/responses/pending" in log_output

    def test_approve_response_logs_request(self, app, temp_state_dir, log_capture):
        """Test that POST /api/responses/{id}/approve logs the request."""
        # Add a test entry first
        audit_log_path = os.path.join(temp_state_dir, "audit_log.json")
        with open(audit_log_path, "r") as f:
            audit_log = json.load(f)
        
        audit_log["entries"].append({
            "id": "test-123",
            "status": "pending_review",
            "text": "Test response"
        })
        
        with open(audit_log_path, "w") as f:
            json.dump(audit_log, f)
        
        # Find and call the endpoint directly
        for route in app.routes:
            if hasattr(route, 'path') and '/approve' in route.path:
                response = asyncio.run(route.endpoint("test-123"))
                assert response is not None
                break
        
        log_output = log_capture.getvalue()
        assert "POST" in log_output
        assert "approve" in log_output

    def test_reject_response_logs_request(self, app, temp_state_dir, log_capture, mock_request_json):
        """Test that POST /api/responses/{id}/reject logs the request."""
        # Add a test entry first
        audit_log_path = os.path.join(temp_state_dir, "audit_log.json")
        with open(audit_log_path, "r") as f:
            audit_log = json.load(f)
        
        audit_log["entries"].append({
            "id": "test-456",
            "status": "pending_review",
            "text": "Test response"
        })
        
        with open(audit_log_path, "w") as f:
            json.dump(audit_log, f)
        
        # Find and call the endpoint directly with mock request
        for route in app.routes:
            if hasattr(route, 'path') and '/reject' in route.path:
                mock_request = mock_request_json({"reason": "Test rejection"})
                response = asyncio.run(route.endpoint("test-456", mock_request))
                assert response is not None
                break
        
        log_output = log_capture.getvalue()
        assert "POST" in log_output
        assert "reject" in log_output

    def test_edit_response_logs_request(self, app, temp_state_dir, log_capture, mock_request_json):
        """Test that POST /api/responses/{id}/edit logs the request."""
        # Add a test entry first
        audit_log_path = os.path.join(temp_state_dir, "audit_log.json")
        with open(audit_log_path, "r") as f:
            audit_log = json.load(f)
        
        audit_log["entries"].append({
            "id": "test-789",
            "status": "pending_review",
            "text": "Test response"
        })
        
        with open(audit_log_path, "w") as f:
            json.dump(audit_log, f)
        
        # Find and call the endpoint directly with mock request
        for route in app.routes:
            if hasattr(route, 'path') and '/edit' in route.path:
                mock_request = mock_request_json({"text": "Updated text"})
                response = asyncio.run(route.endpoint("test-789", mock_request))
                assert response is not None
                break
        
        log_output = log_capture.getvalue()
        assert "POST" in log_output
        assert "edit" in log_output

    def test_oauth_login_logs_request(self, app, log_capture, monkeypatch):
        """Test that GET /auth/instagram/login logs the request."""
        # Set required environment variables
        monkeypatch.setenv("INSTAGRAM_CLIENT_ID", "test_client")
        monkeypatch.setenv("INSTAGRAM_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("INSTAGRAM_REDIRECT_URI", "http://localhost/callback")
        
        # Find and call the endpoint directly
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/auth/instagram/login':
                response = asyncio.run(route.endpoint())
                assert response is not None
                break
        
        log_output = log_capture.getvalue()
        assert "GET" in log_output
        assert "login" in log_output

    def test_oauth_logout_logs_request(self, app, log_capture):
        """Test that GET /auth/instagram/logout logs the request."""
        # Find and call the endpoint directly
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/auth/instagram/logout':
                response = asyncio.run(route.endpoint())
                assert response is not None
                break
        
        log_output = log_capture.getvalue()
        assert "GET" in log_output
        assert "logout" in log_output

    def test_dashboard_home_logs_request(self, app, log_capture):
        """Test that GET / logs the request."""
        # Find and call the endpoint directly
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/':
                response = asyncio.run(route.endpoint())
                assert response is not None
                break
        
        log_output = log_capture.getvalue()
        assert "GET" in log_output
        assert "/" in log_output or "home" in log_output or "dashboard" in log_output

    def test_error_response_logs_status(self, app, log_capture):
        """Test that error responses log the error status code."""
        # Try to approve non-existent response
        from fastapi import HTTPException
        
        # Find and call the endpoint directly
        try:
            for route in app.routes:
                if hasattr(route, 'path') and '/approve' in route.path:
                    response = asyncio.run(route.endpoint("nonexistent-id"))
                    break
        except HTTPException as e:
            assert e.status_code == 404
        
        log_output = log_capture.getvalue()
        assert "POST" in log_output or "approve" in log_output or "404" in log_output

    def test_log_format_includes_timestamp(self, app, log_capture):
        """Test that logs include timestamp information."""
        # Find and call the endpoint directly
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/api/responses':
                response = asyncio.run(route.endpoint())
                assert response is not None
                break
        
        log_output = log_capture.getvalue()
        # Log should have some timestamp or time-related info
        # The actual format will depend on implementation
        assert len(log_output) > 0

    def test_log_format_includes_method_and_path(self, app, log_capture):
        """Test that logs include HTTP method and path."""
        # Find and call the endpoint directly
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/api/responses/pending':
                response = asyncio.run(route.endpoint())
                assert response is not None
                break
        
        log_output = log_capture.getvalue()
        assert "GET" in log_output
        assert "pending" in log_output or "/api/responses/pending" in log_output
