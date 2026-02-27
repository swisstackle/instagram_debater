"""
Unit tests for prompt editor endpoints in dashboard.

Tests follow TDD approach - tests written before implementation.
"""
import asyncio
import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock

import pytest


class TestPromptEditorEndpoints:
    """Test suite for prompt editor API endpoints."""

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
    def prompt_extractor(self, temp_state_dir):
        """Create a LocalDiskPromptExtractor with a temporary state directory."""
        from src.local_disk_prompt_extractor import LocalDiskPromptExtractor
        return LocalDiskPromptExtractor(state_dir=temp_state_dir)

    @pytest.fixture
    def app(self, temp_state_dir, prompt_extractor):
        """Create FastAPI app with temporary state directory and injected prompt extractor."""
        from dashboard import create_dashboard_app
        from src.local_disk_audit_extractor import LocalDiskAuditExtractor

        audit_extractor = LocalDiskAuditExtractor(state_dir=temp_state_dir)
        return create_dashboard_app(
            state_dir=temp_state_dir,
            audit_log_extractor=audit_extractor,
            prompt_extractor=prompt_extractor,
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

    # ================== ENDPOINT EXISTENCE TESTS ==================

    def test_get_prompts_endpoint_exists(self, app):
        """Test that GET /api/prompts endpoint exists."""
        endpoint = self._get_route_endpoint(app, "/api/prompts", "GET")
        assert endpoint is not None, "GET /api/prompts endpoint should exist"

    def test_get_prompt_by_name_endpoint_exists(self, app):
        """Test that GET /api/prompts/{name} endpoint exists."""
        endpoint = self._get_route_endpoint(app, "/api/prompts/{name}", "GET")
        assert endpoint is not None, "GET /api/prompts/{name} endpoint should exist"

    def test_put_prompt_endpoint_exists(self, app):
        """Test that PUT /api/prompts/{name} endpoint exists."""
        endpoint = self._get_route_endpoint(app, "/api/prompts/{name}", "PUT")
        assert endpoint is not None, "PUT /api/prompts/{name} endpoint should exist"

    # ================== GET ALL PROMPTS TESTS ==================

    def test_get_prompts_returns_empty_dict_by_default(self, app):
        """Test that GET /api/prompts returns empty dict when no prompts stored."""
        endpoint = self._get_route_endpoint(app, "/api/prompts", "GET")
        assert endpoint is not None

        response = asyncio.run(endpoint())
        data = json.loads(response.body)
        assert "prompts" in data
        assert data["prompts"] == {}

    def test_get_prompts_returns_existing_prompts(self, app, prompt_extractor):
        """Test that GET /api/prompts returns all stored prompts."""
        prompt_extractor.set_prompt("debate_prompt", "Prompt A content")
        prompt_extractor.set_prompt("relevance_prompt", "Prompt B content")

        endpoint = self._get_route_endpoint(app, "/api/prompts", "GET")
        response = asyncio.run(endpoint())
        data = json.loads(response.body)
        assert len(data["prompts"]) == 2
        assert data["prompts"]["debate_prompt"] == "Prompt A content"
        assert data["prompts"]["relevance_prompt"] == "Prompt B content"

    # ================== GET SINGLE PROMPT TESTS ==================

    def test_get_prompt_by_name_returns_content(self, app, prompt_extractor):
        """Test that GET /api/prompts/{name} returns the stored prompt content."""
        prompt_extractor.set_prompt("debate_prompt", "Debate prompt content")

        endpoint = self._get_route_endpoint(app, "/api/prompts/{name}", "GET")
        assert endpoint is not None

        response = asyncio.run(endpoint("debate_prompt"))
        data = json.loads(response.body)
        assert data["name"] == "debate_prompt"
        assert data["content"] == "Debate prompt content"

    def test_get_prompt_by_name_returns_empty_when_not_set(self, app):
        """Test that GET /api/prompts/{name} returns empty content when prompt not stored."""
        endpoint = self._get_route_endpoint(app, "/api/prompts/{name}", "GET")
        assert endpoint is not None

        response = asyncio.run(endpoint("debate_prompt"))
        data = json.loads(response.body)
        assert data["name"] == "debate_prompt"
        assert data["content"] == ""

    # ================== PUT PROMPT TESTS ==================

    def test_put_prompt_stores_content(self, app, prompt_extractor):
        """Test that PUT /api/prompts/{name} stores the prompt content."""
        endpoint = self._get_route_endpoint(app, "/api/prompts/{name}", "PUT")
        assert endpoint is not None

        mock_request = MagicMock()

        async def mock_json():
            return {"content": "New debate prompt content"}

        mock_request.json = mock_json

        response = asyncio.run(endpoint("debate_prompt", mock_request))
        data = json.loads(response.body)
        assert data["status"] == "ok"
        assert data["name"] == "debate_prompt"

        # Verify it was actually saved
        assert prompt_extractor.get_prompt("debate_prompt") == "New debate prompt content"

    def test_put_prompt_overwrites_existing_content(self, app, prompt_extractor):
        """Test that PUT /api/prompts/{name} overwrites existing prompt content."""
        prompt_extractor.set_prompt("debate_prompt", "Old content")

        endpoint = self._get_route_endpoint(app, "/api/prompts/{name}", "PUT")
        assert endpoint is not None

        mock_request = MagicMock()

        async def mock_json():
            return {"content": "Updated content"}

        mock_request.json = mock_json

        asyncio.run(endpoint("debate_prompt", mock_request))
        assert prompt_extractor.get_prompt("debate_prompt") == "Updated content"

    def test_put_prompt_returns_400_for_missing_content(self, app):
        """Test that PUT /api/prompts/{name} returns 400 when content field is missing."""
        from fastapi import HTTPException

        endpoint = self._get_route_endpoint(app, "/api/prompts/{name}", "PUT")
        assert endpoint is not None

        mock_request = MagicMock()

        async def mock_json():
            return {}  # Missing content field

        mock_request.json = mock_json

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(endpoint("debate_prompt", mock_request))
        assert exc_info.value.status_code == 400

    def test_get_prompt_reflects_put_change(self, app, prompt_extractor):
        """Test that GET /api/prompts/{name} reflects a change made by PUT."""
        put_endpoint = self._get_route_endpoint(app, "/api/prompts/{name}", "PUT")
        get_endpoint = self._get_route_endpoint(app, "/api/prompts/{name}", "GET")
        assert put_endpoint is not None
        assert get_endpoint is not None

        mock_request = MagicMock()

        async def mock_json():
            return {"content": "Freshly set content"}

        mock_request.json = mock_json
        asyncio.run(put_endpoint("debate_prompt", mock_request))

        response = asyncio.run(get_endpoint("debate_prompt"))
        data = json.loads(response.body)
        assert data["content"] == "Freshly set content"

    # ================== UI INCLUSION TEST ==================

    def test_dashboard_home_includes_prompt_editor(self, app):
        """Test that the dashboard home page includes a prompt editor section."""
        for route in app.routes:
            if hasattr(route, "path") and route.path == "/":
                response = asyncio.run(route.endpoint())
                html = response.body.decode("utf-8")
                assert "prompt" in html.lower(), \
                    "Dashboard should include prompt editor section"
                break
