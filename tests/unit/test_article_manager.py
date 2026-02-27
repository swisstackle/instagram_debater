"""
Unit tests for article manager endpoints in dashboard.

Tests follow TDD approach - tests written before implementation.
"""
import asyncio
import json
import os
import shutil
import tempfile

import pytest


class TestArticleManagerEndpoints:
    """Test suite for article manager API endpoints."""

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
    def article_extractor(self, temp_state_dir):
        """Create a LocalDiskArticleExtractor with a temporary state directory."""
        from src.local_disk_article_extractor import LocalDiskArticleExtractor
        return LocalDiskArticleExtractor(state_dir=temp_state_dir)

    @pytest.fixture
    def app(self, temp_state_dir, article_extractor):
        """Create FastAPI app with temporary state directory and injected article extractor."""
        from dashboard import create_dashboard_app
        from src.local_disk_audit_extractor import LocalDiskAuditExtractor

        audit_extractor = LocalDiskAuditExtractor(state_dir=temp_state_dir)
        return create_dashboard_app(
            state_dir=temp_state_dir,
            audit_log_extractor=audit_extractor,
            article_extractor=article_extractor,
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

    def test_get_articles_endpoint_exists(self, app):
        """Test that GET /api/articles endpoint exists."""
        endpoint = self._get_route_endpoint(app, "/api/articles", "GET")
        assert endpoint is not None, "GET /api/articles endpoint should exist"

    def test_post_articles_endpoint_exists(self, app):
        """Test that POST /api/articles endpoint exists."""
        endpoint = self._get_route_endpoint(app, "/api/articles", "POST")
        assert endpoint is not None, "POST /api/articles endpoint should exist"

    def test_put_article_endpoint_exists(self, app):
        """Test that PUT /api/articles/{article_id} endpoint exists."""
        endpoint = self._get_route_endpoint(app, "/api/articles/{article_id}", "PUT")
        assert endpoint is not None, "PUT /api/articles/{article_id} endpoint should exist"

    def test_delete_article_endpoint_exists(self, app):
        """Test that DELETE /api/articles/{article_id} endpoint exists."""
        endpoint = self._get_route_endpoint(app, "/api/articles/{article_id}", "DELETE")
        assert endpoint is not None, "DELETE /api/articles/{article_id} endpoint should exist"

    # ================== GET ARTICLES TESTS ==================

    def test_get_articles_returns_empty_list_by_default(self, app):
        """Test that GET /api/articles returns empty list when no articles exist."""
        endpoint = self._get_route_endpoint(app, "/api/articles", "GET")
        assert endpoint is not None

        response = asyncio.run(endpoint())
        data = json.loads(response.body)
        assert "articles" in data
        assert data["articles"] == []

    def test_get_articles_returns_existing_articles(self, app, article_extractor):
        """Test that GET /api/articles returns all articles."""
        article_extractor.save_article("art1", "Title 1", "Content 1", "https://example.com/1")
        article_extractor.save_article("art2", "Title 2", "Content 2", "https://example.com/2")

        endpoint = self._get_route_endpoint(app, "/api/articles", "GET")
        response = asyncio.run(endpoint())
        data = json.loads(response.body)
        assert len(data["articles"]) == 2

    # ================== POST ARTICLES TESTS ==================

    def test_post_article_creates_article(self, app, article_extractor):
        """Test that POST /api/articles creates a new article."""
        from unittest.mock import MagicMock

        endpoint = self._get_route_endpoint(app, "/api/articles", "POST")
        assert endpoint is not None

        mock_request = MagicMock()

        async def mock_json():
            return {"title": "New Article", "content": "# Content", "link": "https://example.com"}

        mock_request.json = mock_json

        response = asyncio.run(endpoint(mock_request))
        data = json.loads(response.body)
        assert data["status"] == "ok"
        assert "article_id" in data

        # Verify it was actually saved
        articles = article_extractor.get_articles()
        assert len(articles) == 1
        assert articles[0]["title"] == "New Article"

    def test_post_article_returns_400_for_missing_title(self, app):
        """Test that POST /api/articles returns 400 when title is missing."""
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        endpoint = self._get_route_endpoint(app, "/api/articles", "POST")
        assert endpoint is not None

        mock_request = MagicMock()

        async def mock_json():
            return {"content": "# Content", "link": "https://example.com"}

        mock_request.json = mock_json

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(endpoint(mock_request))
        assert exc_info.value.status_code == 400

    def test_post_article_returns_400_for_missing_content(self, app):
        """Test that POST /api/articles returns 400 when content is missing."""
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        endpoint = self._get_route_endpoint(app, "/api/articles", "POST")
        assert endpoint is not None

        mock_request = MagicMock()

        async def mock_json():
            return {"title": "Title", "link": "https://example.com"}

        mock_request.json = mock_json

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(endpoint(mock_request))
        assert exc_info.value.status_code == 400

    # ================== PUT ARTICLE TESTS ==================

    def test_put_article_updates_existing_article(self, app, article_extractor):
        """Test that PUT /api/articles/{article_id} updates an article."""
        from unittest.mock import MagicMock

        article_extractor.save_article("art1", "Old Title", "Old Content", "https://old.com")

        endpoint = self._get_route_endpoint(app, "/api/articles/{article_id}", "PUT")
        assert endpoint is not None

        mock_request = MagicMock()

        async def mock_json():
            return {"title": "New Title", "content": "New Content", "link": "https://new.com"}

        mock_request.json = mock_json

        response = asyncio.run(endpoint("art1", mock_request))
        data = json.loads(response.body)
        assert data["status"] == "ok"

        # Verify update
        article = article_extractor.get_article("art1")
        assert article["title"] == "New Title"
        assert article["content"] == "New Content"

    def test_put_article_returns_404_for_unknown_id(self, app):
        """Test that PUT /api/articles/{article_id} returns 404 for unknown article."""
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        endpoint = self._get_route_endpoint(app, "/api/articles/{article_id}", "PUT")
        assert endpoint is not None

        mock_request = MagicMock()

        async def mock_json():
            return {"title": "Title", "content": "Content", "link": "https://example.com"}

        mock_request.json = mock_json

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(endpoint("nonexistent", mock_request))
        assert exc_info.value.status_code == 404

    # ================== DELETE ARTICLE TESTS ==================

    def test_delete_article_removes_article(self, app, article_extractor):
        """Test that DELETE /api/articles/{article_id} removes the article."""
        article_extractor.save_article("art1", "Title", "Content", "https://example.com")

        endpoint = self._get_route_endpoint(app, "/api/articles/{article_id}", "DELETE")
        assert endpoint is not None

        response = asyncio.run(endpoint("art1"))
        data = json.loads(response.body)
        assert data["status"] == "ok"

        # Verify deletion
        assert article_extractor.get_articles() == []

    def test_delete_article_returns_404_for_unknown_id(self, app):
        """Test that DELETE /api/articles/{article_id} returns 404 for unknown article."""
        from fastapi import HTTPException

        endpoint = self._get_route_endpoint(app, "/api/articles/{article_id}", "DELETE")
        assert endpoint is not None

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(endpoint("nonexistent"))
        assert exc_info.value.status_code == 404

    # ================== UI INCLUSION TEST ==================

    def test_dashboard_home_includes_article_manager(self, app):
        """Test that the dashboard home page includes an article manager section."""
        for route in app.routes:
            if hasattr(route, "path") and route.path == "/":
                response = asyncio.run(route.endpoint())
                html = response.body.decode("utf-8")
                assert "article" in html.lower(), \
                    "Dashboard should include article manager section"
                break
