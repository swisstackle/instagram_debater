"""
Unit tests for mode editor endpoints in dashboard.

Tests follow TDD approach - tests written before implementation.
"""
import asyncio
import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock

import pytest


class TestModeEditorEndpoints:
    """Test suite for mode editor API endpoints."""

    @pytest.fixture
    def temp_state_dir(self):
        """Create a temporary state directory for tests."""
        temp_dir = tempfile.mkdtemp()
        audit_log_path = os.path.join(temp_dir, "audit_log.json")
        with open(audit_log_path, "w") as f:
            json.dump({"version": "1.0", "entries": []}, f)
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mode_extractor(self, temp_state_dir):
        """Create a LocalDiskModeExtractor with a temporary state directory."""
        from src.local_disk_mode_extractor import LocalDiskModeExtractor
        return LocalDiskModeExtractor(state_dir=temp_state_dir)

    @pytest.fixture
    def app(self, temp_state_dir, mode_extractor):
        """Create FastAPI app with temporary state directory and injected mode extractor."""
        from dashboard import create_dashboard_app
        from src.local_disk_audit_extractor import LocalDiskAuditExtractor

        extractor = LocalDiskAuditExtractor(state_dir=temp_state_dir)
        return create_dashboard_app(
            state_dir=temp_state_dir,
            audit_log_extractor=extractor,
            mode_extractor=mode_extractor,
        )

    def _get_route_endpoint(self, app, path, method="GET"):
        """Helper to find a route endpoint by path and method."""
        for route in app.routes:
            if hasattr(route, "path") and route.path == path:
                if hasattr(route, "methods") and method in route.methods:
                    return route.endpoint
                elif not hasattr(route, "methods"):
                    return route.endpoint
        return None

    def test_get_mode_endpoint_exists(self, app):
        """Test that GET /api/mode endpoint exists."""
        endpoint = self._get_route_endpoint(app, "/api/mode", "GET")
        assert endpoint is not None, "GET /api/mode endpoint should exist"

    def test_post_mode_endpoint_exists(self, app):
        """Test that POST /api/mode endpoint exists."""
        endpoint = self._get_route_endpoint(app, "/api/mode", "POST")
        assert endpoint is not None, "POST /api/mode endpoint should exist"

    def test_get_mode_returns_auto_mode_false_by_default(self, app):
        """Test that GET /api/mode returns auto_mode=False when not yet set."""
        endpoint = self._get_route_endpoint(app, "/api/mode", "GET")
        assert endpoint is not None

        response = asyncio.run(endpoint())
        data = json.loads(response.body)
        assert data["auto_mode"] is False

    def test_get_mode_returns_auto_mode_true_when_enabled(self, app, mode_extractor):
        """Test that GET /api/mode returns auto_mode=True when extractor has it enabled."""
        mode_extractor.set_auto_mode(True)
        endpoint = self._get_route_endpoint(app, "/api/mode", "GET")
        assert endpoint is not None

        response = asyncio.run(endpoint())
        data = json.loads(response.body)
        assert data["auto_mode"] is True

    def test_post_mode_enables_auto_mode(self, app, mode_extractor):
        """Test that POST /api/mode with auto_mode=True enables auto mode."""
        endpoint = self._get_route_endpoint(app, "/api/mode", "POST")
        assert endpoint is not None

        mock_request = MagicMock()

        async def mock_json():
            return {"auto_mode": True}

        mock_request.json = mock_json

        response = asyncio.run(endpoint(mock_request))
        data = json.loads(response.body)
        assert data["status"] == "ok"
        assert data["auto_mode"] is True
        assert mode_extractor.get_auto_mode() is True

    def test_post_mode_disables_auto_mode(self, app, mode_extractor):
        """Test that POST /api/mode with auto_mode=False disables auto mode."""
        mode_extractor.set_auto_mode(True)
        endpoint = self._get_route_endpoint(app, "/api/mode", "POST")
        assert endpoint is not None

        mock_request = MagicMock()

        async def mock_json():
            return {"auto_mode": False}

        mock_request.json = mock_json

        response = asyncio.run(endpoint(mock_request))
        data = json.loads(response.body)
        assert data["status"] == "ok"
        assert data["auto_mode"] is False
        assert mode_extractor.get_auto_mode() is False

    def test_post_mode_rejects_invalid_input(self, app):
        """Test that POST /api/mode returns 400 for missing or non-boolean auto_mode."""
        from fastapi import HTTPException

        endpoint = self._get_route_endpoint(app, "/api/mode", "POST")
        assert endpoint is not None

        mock_request = MagicMock()

        async def mock_json():
            return {"auto_mode": "yes"}  # string instead of bool

        mock_request.json = mock_json

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(endpoint(mock_request))
        assert exc_info.value.status_code == 400

    def test_get_mode_reflects_post_mode_change(self, app, mode_extractor):
        """Test that GET /api/mode reflects the change made by POST /api/mode."""
        post_endpoint = self._get_route_endpoint(app, "/api/mode", "POST")
        get_endpoint = self._get_route_endpoint(app, "/api/mode", "GET")
        assert post_endpoint is not None
        assert get_endpoint is not None

        # Enable auto mode
        mock_request = MagicMock()

        async def mock_json():
            return {"auto_mode": True}

        mock_request.json = mock_json
        asyncio.run(post_endpoint(mock_request))

        # Verify GET reflects the change
        response = asyncio.run(get_endpoint())
        data = json.loads(response.body)
        assert data["auto_mode"] is True

    def test_dashboard_home_includes_mode_toggle(self, app):
        """Test that the dashboard home page includes a mode toggle element."""
        for route in app.routes:
            if hasattr(route, "path") and route.path == "/":
                response = asyncio.run(route.endpoint())
                html = response.body.decode("utf-8")
                assert "mode-toggle" in html or "auto-mode" in html or "auto_mode" in html, \
                    "Dashboard should include mode toggle element"
                break

