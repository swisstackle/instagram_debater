"""
Unit tests for ArticleExtractor implementations.

Tests follow TDD approach - tests written before implementation.
"""
import json
import os

import pytest

from tests.unit.test_extractor_base import BaseLocalDiskExtractorTests, BaseTigrisExtractorTests


class TestLocalDiskArticleExtractor(BaseLocalDiskExtractorTests):
    """Test suite for LocalDiskArticleExtractor."""

    @pytest.fixture
    def extractor(self, temp_state_dir):
        """Create a LocalDiskArticleExtractor instance."""
        from src.local_disk_article_extractor import LocalDiskArticleExtractor
        return LocalDiskArticleExtractor(state_dir=temp_state_dir)

    def test_implements_interface(self, extractor):
        """Test that LocalDiskArticleExtractor implements ArticleExtractor interface."""
        from src.article_extractor import ArticleExtractor
        assert isinstance(extractor, ArticleExtractor)

    def test_get_articles_empty_by_default(self, extractor):
        """Test that get_articles returns empty list when no file exists."""
        assert extractor.get_articles() == []

    def test_save_and_get_article(self, extractor):
        """Test saving an article and retrieving it."""
        extractor.save_article("art1", "Title 1", "# Content 1", "https://example.com/1")
        articles = extractor.get_articles()
        assert len(articles) == 1
        assert articles[0]["id"] == "art1"
        assert articles[0]["title"] == "Title 1"
        assert articles[0]["content"] == "# Content 1"
        assert articles[0]["link"] == "https://example.com/1"

    def test_save_multiple_articles(self, extractor):
        """Test saving multiple articles."""
        extractor.save_article("art1", "Title 1", "Content 1", "https://example.com/1")
        extractor.save_article("art2", "Title 2", "Content 2", "https://example.com/2")
        articles = extractor.get_articles()
        assert len(articles) == 2

    def test_get_article_by_id(self, extractor):
        """Test getting a single article by ID."""
        extractor.save_article("art1", "Title 1", "Content 1", "https://example.com/1")
        extractor.save_article("art2", "Title 2", "Content 2", "https://example.com/2")
        article = extractor.get_article("art1")
        assert article is not None
        assert article["id"] == "art1"
        assert article["title"] == "Title 1"

    def test_get_article_not_found_returns_none(self, extractor):
        """Test that get_article returns None for unknown ID."""
        assert extractor.get_article("nonexistent") is None

    def test_update_existing_article(self, extractor):
        """Test updating an existing article."""
        extractor.save_article("art1", "Title 1", "Content 1", "https://example.com/1")
        extractor.save_article("art1", "Updated Title", "Updated Content", "https://example.com/updated")
        articles = extractor.get_articles()
        assert len(articles) == 1
        assert articles[0]["title"] == "Updated Title"
        assert articles[0]["content"] == "Updated Content"
        assert articles[0]["link"] == "https://example.com/updated"

    def test_delete_existing_article(self, extractor):
        """Test deleting an existing article."""
        extractor.save_article("art1", "Title 1", "Content 1", "https://example.com/1")
        result = extractor.delete_article("art1")
        assert result is True
        assert extractor.get_articles() == []

    def test_delete_nonexistent_article_returns_false(self, extractor):
        """Test that delete_article returns False for unknown ID."""
        result = extractor.delete_article("nonexistent")
        assert result is False

    def test_delete_does_not_affect_other_articles(self, extractor):
        """Test that deleting one article doesn't affect others."""
        extractor.save_article("art1", "Title 1", "Content 1", "https://example.com/1")
        extractor.save_article("art2", "Title 2", "Content 2", "https://example.com/2")
        extractor.delete_article("art1")
        articles = extractor.get_articles()
        assert len(articles) == 1
        assert articles[0]["id"] == "art2"

    def test_persists_to_file(self, extractor, temp_state_dir):
        """Test that articles are persisted to disk."""
        extractor.save_article("art1", "Title 1", "Content 1", "https://example.com/1")
        articles_file = os.path.join(temp_state_dir, "articles.json")
        assert os.path.exists(articles_file)
        with open(articles_file, "r") as f:
            data = json.load(f)
        assert len(data["articles"]) == 1
        assert data["articles"][0]["id"] == "art1"

    def test_loads_from_existing_file(self, temp_state_dir):
        """Test that articles are loaded from an existing file."""
        from src.local_disk_article_extractor import LocalDiskArticleExtractor
        articles_file = os.path.join(temp_state_dir, "articles.json")
        with open(articles_file, "w") as f:
            json.dump({"articles": [{"id": "art1", "title": "T", "content": "C", "link": "L"}]}, f)
        extractor = LocalDiskArticleExtractor(state_dir=temp_state_dir)
        articles = extractor.get_articles()
        assert len(articles) == 1
        assert articles[0]["id"] == "art1"


class TestTigrisArticleExtractor(BaseTigrisExtractorTests):
    """Test suite for TigrisArticleExtractor using mocked S3."""

    @pytest.fixture
    def extractor(self, mock_s3_client, monkeypatch):
        """Create a TigrisArticleExtractor with mocked S3 client."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
        monkeypatch.setenv("TIGRIS_BUCKET_NAME", "test-bucket")
        from src.tigris_article_extractor import TigrisArticleExtractor
        ext = TigrisArticleExtractor()
        ext.s3_client = mock_s3_client
        return ext

    def test_implements_interface(self, extractor):
        """Test that TigrisArticleExtractor implements ArticleExtractor interface."""
        from src.article_extractor import ArticleExtractor
        assert isinstance(extractor, ArticleExtractor)

    def test_get_articles_empty_when_no_key(self, extractor, mock_s3_client):
        """Test get_articles returns empty list when S3 object doesn't exist."""
        self.setup_mock_no_such_key(mock_s3_client)
        assert extractor.get_articles() == []

    def test_get_articles_from_s3(self, extractor, mock_s3_client):
        """Test get_articles returns articles from S3."""
        self.setup_mock_get_object(
            mock_s3_client,
            {"articles": [{"id": "art1", "title": "T", "content": "C", "link": "L"}]}
        )
        articles = extractor.get_articles()
        assert len(articles) == 1
        assert articles[0]["id"] == "art1"

    def test_get_article_by_id(self, extractor, mock_s3_client):
        """Test get_article returns a specific article from S3."""
        self.setup_mock_get_object(
            mock_s3_client,
            {"articles": [
                {"id": "art1", "title": "T1", "content": "C1", "link": "L1"},
                {"id": "art2", "title": "T2", "content": "C2", "link": "L2"},
            ]}
        )
        article = extractor.get_article("art1")
        assert article is not None
        assert article["title"] == "T1"

    def test_get_article_not_found_returns_none(self, extractor, mock_s3_client):
        """Test get_article returns None when article not found."""
        self.setup_mock_no_such_key(mock_s3_client)
        assert extractor.get_article("nonexistent") is None

    def test_save_article_creates_in_s3(self, extractor, mock_s3_client):
        """Test that save_article saves data to S3."""
        self.setup_mock_no_such_key(mock_s3_client)
        extractor.save_article("art1", "Title", "Content", "https://example.com")
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        saved_data = json.loads(call_kwargs["Body"])
        assert len(saved_data["articles"]) == 1
        assert saved_data["articles"][0]["id"] == "art1"

    def test_save_article_updates_existing_in_s3(self, extractor, mock_s3_client):
        """Test that save_article updates an existing article in S3."""
        self.setup_mock_get_object(
            mock_s3_client,
            {"articles": [{"id": "art1", "title": "Old", "content": "Old", "link": "Old"}]}
        )
        extractor.save_article("art1", "New", "New Content", "https://new.com")
        call_kwargs = mock_s3_client.put_object.call_args[1]
        saved_data = json.loads(call_kwargs["Body"])
        assert len(saved_data["articles"]) == 1
        assert saved_data["articles"][0]["title"] == "New"

    def test_delete_article_from_s3(self, extractor, mock_s3_client):
        """Test that delete_article removes article from S3."""
        self.setup_mock_get_object(
            mock_s3_client,
            {"articles": [{"id": "art1", "title": "T", "content": "C", "link": "L"}]}
        )
        result = extractor.delete_article("art1")
        assert result is True
        call_kwargs = mock_s3_client.put_object.call_args[1]
        saved_data = json.loads(call_kwargs["Body"])
        assert saved_data["articles"] == []

    def test_delete_nonexistent_article_returns_false(self, extractor, mock_s3_client):
        """Test that delete_article returns False when article not found in S3."""
        self.setup_mock_no_such_key(mock_s3_client)
        result = extractor.delete_article("nonexistent")
        assert result is False

    def test_object_key_is_correct(self, extractor):
        """Test that the S3 object key is correct."""
        assert extractor._get_object_key() == "state/articles.json"


class TestArticleExtractorFactory:
    """Test suite for article extractor factory function."""

    def test_factory_returns_local_by_default(self, monkeypatch):
        """Test factory returns LocalDiskArticleExtractor when ARTICLE_STORAGE_TYPE not set."""
        monkeypatch.delenv("ARTICLE_STORAGE_TYPE", raising=False)
        from src.article_extractor_factory import create_article_extractor
        from src.local_disk_article_extractor import LocalDiskArticleExtractor
        extractor = create_article_extractor()
        assert isinstance(extractor, LocalDiskArticleExtractor)

    def test_factory_returns_local_explicitly(self, monkeypatch):
        """Test factory returns LocalDiskArticleExtractor when ARTICLE_STORAGE_TYPE=local."""
        monkeypatch.setenv("ARTICLE_STORAGE_TYPE", "local")
        from src.article_extractor_factory import create_article_extractor
        from src.local_disk_article_extractor import LocalDiskArticleExtractor
        extractor = create_article_extractor()
        assert isinstance(extractor, LocalDiskArticleExtractor)

    def test_factory_returns_tigris(self, monkeypatch):
        """Test factory returns TigrisArticleExtractor when ARTICLE_STORAGE_TYPE=tigris."""
        monkeypatch.setenv("ARTICLE_STORAGE_TYPE", "tigris")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
        monkeypatch.setenv("TIGRIS_BUCKET_NAME", "test-bucket")
        from src.article_extractor_factory import create_article_extractor
        from src.tigris_article_extractor import TigrisArticleExtractor
        extractor = create_article_extractor()
        assert isinstance(extractor, TigrisArticleExtractor)
