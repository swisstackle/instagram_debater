"""
Unit tests for the Posted tab in the dashboard.

Tests follow TDD approach - tests written before implementation.
"""
import asyncio
import json
import os
import shutil
import tempfile

import pytest


class TestPostedTabEndpoints:
    """Test suite for the Posted tab API endpoint and dashboard UI."""

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
    def audit_extractor(self, temp_state_dir):
        """Create a LocalDiskAuditExtractor with a temporary state directory."""
        from src.local_disk_audit_extractor import LocalDiskAuditExtractor
        return LocalDiskAuditExtractor(state_dir=temp_state_dir)

    @pytest.fixture
    def app(self, temp_state_dir, audit_extractor):
        """Create FastAPI app with temporary state directory and injected audit extractor."""
        from dashboard import create_dashboard_app
        return create_dashboard_app(
            state_dir=temp_state_dir,
            audit_log_extractor=audit_extractor,
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

    def test_get_posted_responses_endpoint_exists(self, app):
        """Test that GET /api/responses/posted endpoint exists."""
        endpoint = self._get_route_endpoint(app, "/api/responses/posted", "GET")
        assert endpoint is not None, "GET /api/responses/posted endpoint should exist"

    # ================== GET POSTED RESPONSES TESTS ==================

    def test_get_posted_responses_returns_empty_list_when_none_posted(self, app):
        """Test that GET /api/responses/posted returns empty list when no entries are posted."""
        endpoint = self._get_route_endpoint(app, "/api/responses/posted", "GET")
        assert endpoint is not None

        response = asyncio.run(endpoint())
        data = json.loads(response.body)
        assert "responses" in data
        assert data["responses"] == []

    def test_get_posted_responses_returns_only_posted_entries(self, app, audit_extractor):
        """Test that GET /api/responses/posted returns only entries with posted=True."""
        # Add a posted entry
        audit_extractor.save_entry({
            "comment_id": "ig_comment_001",
            "comment_text": "Test comment",
            "generated_response": "Test response",
            "status": "approved",
            "posted": True,
            "posted_at": "2026-01-01T00:00:00Z",
        })
        # Add a non-posted entry
        audit_extractor.save_entry({
            "comment_id": "ig_comment_002",
            "comment_text": "Another comment",
            "generated_response": "Another response",
            "status": "pending_review",
            "posted": False,
        })

        endpoint = self._get_route_endpoint(app, "/api/responses/posted", "GET")
        response = asyncio.run(endpoint())
        data = json.loads(response.body)

        assert len(data["responses"]) == 1
        assert data["responses"][0]["comment_id"] == "ig_comment_001"
        assert data["responses"][0]["posted"] is True

    def test_get_posted_responses_excludes_unposted_entries(self, app, audit_extractor):
        """Test that unposted entries are excluded from /api/responses/posted."""
        audit_extractor.save_entry({
            "comment_id": "ig_comment_003",
            "comment_text": "Pending comment",
            "generated_response": "Pending response",
            "status": "pending_review",
        })

        endpoint = self._get_route_endpoint(app, "/api/responses/posted", "GET")
        response = asyncio.run(endpoint())
        data = json.loads(response.body)

        assert data["responses"] == []

    def test_get_posted_responses_includes_comment_id(self, app, audit_extractor):
        """Test that posted responses include the comment_id field."""
        audit_extractor.save_entry({
            "comment_id": "ig_comment_posted_123",
            "comment_text": "Some comment",
            "generated_response": "Some response",
            "status": "approved",
            "posted": True,
            "posted_at": "2026-02-01T12:00:00Z",
        })

        endpoint = self._get_route_endpoint(app, "/api/responses/posted", "GET")
        response = asyncio.run(endpoint())
        data = json.loads(response.body)

        assert len(data["responses"]) == 1
        assert "comment_id" in data["responses"][0]
        assert data["responses"][0]["comment_id"] == "ig_comment_posted_123"

    def test_get_posted_responses_multiple_posted_entries(self, app, audit_extractor):
        """Test that multiple posted entries are all returned."""
        for i in range(3):
            audit_extractor.save_entry({
                "comment_id": f"ig_comment_{i}",
                "comment_text": f"Comment {i}",
                "generated_response": f"Response {i}",
                "status": "approved",
                "posted": True,
                "posted_at": "2026-01-01T00:00:00Z",
            })

        endpoint = self._get_route_endpoint(app, "/api/responses/posted", "GET")
        response = asyncio.run(endpoint())
        data = json.loads(response.body)

        assert len(data["responses"]) == 3

    # ================== LOGGING TESTS ==================

    def test_get_posted_responses_logs_request(self, app):
        """Test that GET /api/responses/posted logs the request."""
        import logging
        from io import StringIO

        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.INFO)
        logger = logging.getLogger("dashboard")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        try:
            endpoint = self._get_route_endpoint(app, "/api/responses/posted", "GET")
            assert endpoint is not None
            asyncio.run(endpoint())
            log_output = log_stream.getvalue()
            assert "GET /api/responses/posted" in log_output
        finally:
            logger.removeHandler(handler)
            handler.close()

    # ================== DASHBOARD UI TESTS ==================

    def test_dashboard_html_contains_posted_tab(self, app):
        """Test that the dashboard HTML includes a Posted filter tab button."""
        endpoint = self._get_route_endpoint(app, "/", "GET")
        assert endpoint is not None

        response = asyncio.run(endpoint())
        html = response.body.decode("utf-8")
        assert 'data-filter="posted"' in html

    def test_dashboard_html_posted_tab_label(self, app):
        """Test that the Posted tab button has a readable label."""
        endpoint = self._get_route_endpoint(app, "/", "GET")
        assert endpoint is not None

        response = asyncio.run(endpoint())
        html = response.body.decode("utf-8")
        assert "Posted" in html

    def test_dashboard_html_shows_comment_id_for_posted(self, app):
        """Test that the dashboard renders comment_id info for posted entries."""
        endpoint = self._get_route_endpoint(app, "/", "GET")
        assert endpoint is not None

        response = asyncio.run(endpoint())
        html = response.body.decode("utf-8")
        # The JS should reference comment_id for posted entries
        assert "comment_id" in html

    def test_dashboard_js_handles_posted_filter(self, app):
        """Test that the JS getFilteredResponses function handles posted filter."""
        endpoint = self._get_route_endpoint(app, "/", "GET")
        assert endpoint is not None

        response = asyncio.run(endpoint())
        html = response.body.decode("utf-8")
        # The JS should have logic to filter by posted status
        assert "posted" in html

    def test_dashboard_js_approved_filter_excludes_posted(self, app):
        """Test that the JS approved filter excludes already-posted entries."""
        endpoint = self._get_route_endpoint(app, "/", "GET")
        assert endpoint is not None

        response = asyncio.run(endpoint())
        html = response.body.decode("utf-8")
        # The approved filter logic must exclude posted entries
        assert "!r.posted" in html or "r.posted === false" in html or "!r.posted" in html
