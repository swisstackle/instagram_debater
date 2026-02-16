"""
Unit tests for comment extractors.
"""
import json
import os
from unittest.mock import patch, MagicMock

import pytest

from src.comment_extractor import CommentExtractor
from src.local_disk_extractor import LocalDiskExtractor
from src.tigris_extractor import TigrisExtractor
from tests.unit.test_extractor_base import BaseLocalDiskExtractorTests, BaseTigrisExtractorTests


class TestLocalDiskExtractor(BaseLocalDiskExtractorTests):
    """Test suite for LocalDiskExtractor."""

    @pytest.fixture
    def extractor(self, temp_state_dir):
        """Create a LocalDiskExtractor instance."""
        return LocalDiskExtractor(state_dir=temp_state_dir)

    def test_implements_interface(self, extractor):
        """Test that LocalDiskExtractor implements CommentExtractor interface."""
        assert isinstance(extractor, CommentExtractor)

    def test_load_pending_comments_file_not_exists(self, extractor):
        """Test loading pending comments when file doesn't exist."""
        comments = extractor.load_pending_comments()
        assert comments == []

    def test_load_pending_comments_file_exists(self, extractor, temp_state_dir):
        """Test loading pending comments from existing file."""
        # Create test file
        pending_file = os.path.join(temp_state_dir, "pending_comments.json")
        test_data = {
            "version": "1.0",
            "comments": [
                {"comment_id": "123", "text": "Test comment 1"},
                {"comment_id": "456", "text": "Test comment 2"}
            ]
        }
        with open(pending_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        # Load and verify
        comments = extractor.load_pending_comments()
        assert len(comments) == 2
        assert comments[0]["comment_id"] == "123"
        assert comments[1]["comment_id"] == "456"

    def test_save_pending_comment(self, extractor, temp_state_dir):
        """Test saving a pending comment."""
        comment_data = {
            "comment_id": "789",
            "post_id": "post_123",
            "username": "testuser",
            "text": "Test comment"
        }

        extractor.save_pending_comment(comment_data)

        # Verify file was created and contains comment
        pending_file = os.path.join(temp_state_dir, "pending_comments.json")
        assert os.path.exists(pending_file)

        with open(pending_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert len(data["comments"]) == 1
        assert data["comments"][0]["comment_id"] == "789"

    def test_save_pending_comment_appends(self, extractor, temp_state_dir):
        """Test that saving multiple comments appends them."""
        comment1 = {"comment_id": "111", "text": "Comment 1"}
        comment2 = {"comment_id": "222", "text": "Comment 2"}

        extractor.save_pending_comment(comment1)
        extractor.save_pending_comment(comment2)

        # Verify both comments are present
        comments = extractor.load_pending_comments()
        assert len(comments) == 2
        assert comments[0]["comment_id"] == "111"
        assert comments[1]["comment_id"] == "222"

    def test_clear_pending_comments(self, extractor, temp_state_dir):
        """Test clearing pending comments."""
        # Add some comments
        comment = {"comment_id": "123", "text": "Test"}
        extractor.save_pending_comment(comment)

        # Verify comment exists
        comments = extractor.load_pending_comments()
        assert len(comments) == 1

        # Clear and verify
        extractor.clear_pending_comments()
        comments = extractor.load_pending_comments()
        assert len(comments) == 0

    def test_clear_pending_comments_file_not_exists(self, extractor):
        """Test clearing when file doesn't exist (should not raise error)."""
        extractor.clear_pending_comments()  # Should not raise


class TestTigrisExtractor(BaseTigrisExtractorTests):
    """Test suite for TigrisExtractor."""

    @pytest.fixture
    def extractor(self, mock_s3_client):
        """Create a TigrisExtractor instance with mocked S3 client."""
        with patch('src.base_json_extractor.boto3') as mock_boto3:
            mock_boto3.client.return_value = mock_s3_client
            extractor = TigrisExtractor(
                access_key_id="test_key",
                secret_access_key="test_secret",
                endpoint_url="https://fly.storage.tigris.dev",
                bucket_name="test-bucket",
                region="auto"
            )
            extractor.s3_client = mock_s3_client
            return extractor

    def test_implements_interface(self, extractor):
        """Test that TigrisExtractor implements CommentExtractor interface."""
        assert isinstance(extractor, CommentExtractor)

    def test_load_pending_comments_object_exists(self, extractor, mock_s3_client):
        """Test loading pending comments when S3 object exists."""
        test_data = {
            "version": "1.0",
            "comments": [
                {"comment_id": "123", "text": "Test comment 1"},
                {"comment_id": "456", "text": "Test comment 2"}
            ]
        }
        self.setup_mock_get_object(mock_s3_client, test_data)

        comments = extractor.load_pending_comments()

        assert len(comments) == 2
        assert comments[0]["comment_id"] == "123"
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="state/pending_comments.json"
        )

    def test_load_pending_comments_object_not_exists(self, extractor, mock_s3_client):
        """Test loading pending comments when S3 object doesn't exist."""
        self.setup_mock_no_such_key(mock_s3_client)

        comments = extractor.load_pending_comments()

        assert comments == []

    def test_save_pending_comment(self, extractor, mock_s3_client):
        """Test saving a pending comment to S3."""
        # Setup: object doesn't exist initially
        self.setup_mock_no_such_key(mock_s3_client)

        comment_data = {
            "comment_id": "789",
            "post_id": "post_123",
            "username": "testuser",
            "text": "Test comment"
        }

        extractor.save_pending_comment(comment_data)

        # Verify put_object was called
        assert mock_s3_client.put_object.called
        call_args = mock_s3_client.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert call_args[1]["Key"] == "state/pending_comments.json"
        
        # Verify the body contains our comment
        body_data = json.loads(call_args[1]["Body"])
        assert len(body_data["comments"]) == 1
        assert body_data["comments"][0]["comment_id"] == "789"

    def test_save_pending_comment_appends(self, extractor, mock_s3_client):
        """Test that saving multiple comments appends them."""
        # Setup: object exists with one comment
        existing_data = {
            "version": "1.0",
            "comments": [{"comment_id": "111", "text": "Existing comment"}]
        }
        self.setup_mock_get_object(mock_s3_client, existing_data)

        new_comment = {"comment_id": "222", "text": "New comment"}
        extractor.save_pending_comment(new_comment)

        # Verify put_object was called with both comments
        call_args = mock_s3_client.put_object.call_args
        body_data = json.loads(call_args[1]["Body"])
        assert len(body_data["comments"]) == 2
        assert body_data["comments"][0]["comment_id"] == "111"
        assert body_data["comments"][1]["comment_id"] == "222"

    def test_clear_pending_comments(self, extractor, mock_s3_client):
        """Test clearing pending comments in S3."""
        extractor.clear_pending_comments()

        # Verify put_object was called with empty comments list
        call_args = mock_s3_client.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert call_args[1]["Key"] == "state/pending_comments.json"
        
        body_data = json.loads(call_args[1]["Body"])
        assert body_data["comments"] == []

    def test_initialization_with_env_vars(self):
        """Test TigrisExtractor initialization from environment variables."""
        with patch.dict(os.environ, {
            'AWS_ACCESS_KEY_ID': 'env_key',
            'AWS_SECRET_ACCESS_KEY': 'env_secret',
            'AWS_ENDPOINT_URL_S3': 'https://env.endpoint.com',
            'TIGRIS_BUCKET_NAME': 'env-bucket',
            'AWS_REGION': 'env-region'
        }):
            with patch('src.base_json_extractor.boto3') as mock_boto3:
                extractor = TigrisExtractor()
                
                # Verify boto3 client was initialized with correct params
                mock_boto3.client.assert_called_once()
                call_kwargs = mock_boto3.client.call_args[1]
                assert call_kwargs['aws_access_key_id'] == 'env_key'
                assert call_kwargs['aws_secret_access_key'] == 'env_secret'
                assert call_kwargs['endpoint_url'] == 'https://env.endpoint.com'
                assert call_kwargs['region_name'] == 'env-region'


class TestExtractorFactory:
    """Test suite for extractor factory function."""

    def test_create_local_disk_extractor(self):
        """Test creating local disk extractor via factory."""
        from src.comment_extractor_factory import create_comment_extractor
        
        with patch.dict(os.environ, {'COMMENT_STORAGE_TYPE': 'local'}):
            extractor = create_comment_extractor()
            assert isinstance(extractor, LocalDiskExtractor)

    def test_create_tigris_extractor(self):
        """Test creating Tigris extractor via factory."""
        from src.comment_extractor_factory import create_comment_extractor
        
        with patch.dict(os.environ, {
            'COMMENT_STORAGE_TYPE': 'tigris',
            'AWS_ACCESS_KEY_ID': 'test_key',
            'AWS_SECRET_ACCESS_KEY': 'test_secret',
            'AWS_ENDPOINT_URL_S3': 'https://test.endpoint.com',
            'TIGRIS_BUCKET_NAME': 'test-bucket',
            'AWS_REGION': 'auto'
        }):
            with patch('src.base_json_extractor.boto3'):
                extractor = create_comment_extractor()
                assert isinstance(extractor, TigrisExtractor)

    def test_default_to_local_disk(self):
        """Test that factory defaults to local disk when no type specified."""
        from src.comment_extractor_factory import create_comment_extractor
        
        with patch.dict(os.environ, {}, clear=True):
            extractor = create_comment_extractor()
            assert isinstance(extractor, LocalDiskExtractor)
