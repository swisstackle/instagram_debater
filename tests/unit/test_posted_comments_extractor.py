"""
Unit tests for posted comments extractors.
"""
import json
import os
from unittest.mock import patch, MagicMock

import pytest

from src.posted_comments_extractor import PostedCommentsExtractor
from src.local_disk_posted_extractor import LocalDiskPostedExtractor
from src.tigris_posted_extractor import TigrisPostedExtractor
from tests.unit.test_extractor_base import BaseLocalDiskExtractorTests, BaseTigrisExtractorTests


class TestLocalDiskPostedExtractor(BaseLocalDiskExtractorTests):
    """Test suite for LocalDiskPostedExtractor."""

    @pytest.fixture
    def extractor(self, temp_state_dir):
        """Create a LocalDiskPostedExtractor instance."""
        return LocalDiskPostedExtractor(state_dir=temp_state_dir)

    def test_implements_interface(self, extractor):
        """Test that LocalDiskPostedExtractor implements PostedCommentsExtractor interface."""
        assert isinstance(extractor, PostedCommentsExtractor)

    def test_load_posted_ids_file_not_exists(self, extractor):
        """Test loading posted IDs when file doesn't exist."""
        posted_ids = extractor.load_posted_ids()
        assert posted_ids == set()

    def test_load_posted_ids_file_exists(self, extractor, temp_state_dir):
        """Test loading posted IDs from existing file."""
        # Create test file
        posted_file = os.path.join(temp_state_dir, "posted_ids.txt")
        with open(posted_file, 'w', encoding='utf-8') as f:
            f.write("comment_123\n")
            f.write("comment_456\n")
            f.write("comment_789\n")

        # Load and verify
        posted_ids = extractor.load_posted_ids()
        assert len(posted_ids) == 3
        assert "comment_123" in posted_ids
        assert "comment_456" in posted_ids
        assert "comment_789" in posted_ids

    def test_load_posted_ids_ignores_empty_lines(self, extractor, temp_state_dir):
        """Test that loading posted IDs ignores empty lines."""
        # Create test file with empty lines
        posted_file = os.path.join(temp_state_dir, "posted_ids.txt")
        with open(posted_file, 'w', encoding='utf-8') as f:
            f.write("comment_123\n")
            f.write("\n")
            f.write("comment_456\n")
            f.write("\n")

        # Load and verify
        posted_ids = extractor.load_posted_ids()
        assert len(posted_ids) == 2
        assert "comment_123" in posted_ids
        assert "comment_456" in posted_ids

    def test_is_posted_returns_false_when_not_posted(self, extractor):
        """Test that is_posted returns False for new comment IDs."""
        assert extractor.is_posted("new_comment_123") is False

    def test_is_posted_returns_true_after_adding(self, extractor):
        """Test that is_posted returns True after adding comment ID."""
        extractor.add_posted_id("comment_123")
        assert extractor.is_posted("comment_123") is True

    def test_is_posted_returns_true_for_existing_id(self, extractor, temp_state_dir):
        """Test that is_posted returns True for existing ID in file."""
        # Create test file
        posted_file = os.path.join(temp_state_dir, "posted_ids.txt")
        with open(posted_file, 'w', encoding='utf-8') as f:
            f.write("existing_comment\n")

        # Check
        assert extractor.is_posted("existing_comment") is True
        assert extractor.is_posted("new_comment") is False

    def test_add_posted_id(self, extractor, temp_state_dir):
        """Test adding a posted ID."""
        extractor.add_posted_id("comment_123")

        # Verify file was created and contains ID
        posted_file = os.path.join(temp_state_dir, "posted_ids.txt")
        assert os.path.exists(posted_file)

        with open(posted_file, 'r', encoding='utf-8') as f:
            content = f.read()

        assert "comment_123\n" in content

    def test_add_posted_id_appends(self, extractor, temp_state_dir):
        """Test that adding multiple IDs appends them."""
        extractor.add_posted_id("comment_111")
        extractor.add_posted_id("comment_222")
        extractor.add_posted_id("comment_333")

        # Verify file contains all IDs
        posted_file = os.path.join(temp_state_dir, "posted_ids.txt")
        with open(posted_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        assert len(lines) == 3
        assert "comment_111\n" in lines
        assert "comment_222\n" in lines
        assert "comment_333\n" in lines

    def test_add_posted_id_does_not_duplicate(self, extractor):
        """Test that adding the same ID twice doesn't create duplicates."""
        extractor.add_posted_id("comment_123")
        extractor.add_posted_id("comment_123")

        posted_ids = extractor.load_posted_ids()
        assert len(posted_ids) == 1
        assert "comment_123" in posted_ids


class TestTigrisPostedExtractor(BaseTigrisExtractorTests):
    """Test suite for TigrisPostedExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create a TigrisPostedExtractor instance with mocked S3 client."""
        with patch('src.base_json_extractor.boto3') as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.client.return_value = mock_s3
            
            extractor = TigrisPostedExtractor(
                access_key_id="test_key",
                secret_access_key="test_secret",
                endpoint_url="https://test.endpoint.com",
                bucket_name="test-bucket"
            )
            extractor.s3_client = mock_s3
            yield extractor

    def test_implements_interface(self, extractor):
        """Test that TigrisPostedExtractor implements PostedCommentsExtractor interface."""
        assert isinstance(extractor, PostedCommentsExtractor)

    def test_load_posted_ids_object_not_exists(self, extractor):
        """Test loading posted IDs when S3 object doesn't exist."""
        from botocore.exceptions import ClientError
        extractor.s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}},
            "get_object"
        )

        posted_ids = extractor.load_posted_ids()
        assert posted_ids == set()

    def test_load_posted_ids_object_exists(self, extractor):
        """Test loading posted IDs from existing S3 object."""
        # Mock S3 response
        mock_body = MagicMock()
        mock_body.read.return_value = b"comment_123\ncomment_456\ncomment_789\n"
        extractor.s3_client.get_object.return_value = {"Body": mock_body}

        # Load and verify
        posted_ids = extractor.load_posted_ids()
        assert len(posted_ids) == 3
        assert "comment_123" in posted_ids
        assert "comment_456" in posted_ids
        assert "comment_789" in posted_ids

    def test_load_posted_ids_ignores_empty_lines(self, extractor):
        """Test that loading posted IDs ignores empty lines."""
        # Mock S3 response with empty lines
        mock_body = MagicMock()
        mock_body.read.return_value = b"comment_123\n\ncomment_456\n\n"
        extractor.s3_client.get_object.return_value = {"Body": mock_body}

        # Load and verify
        posted_ids = extractor.load_posted_ids()
        assert len(posted_ids) == 2
        assert "comment_123" in posted_ids
        assert "comment_456" in posted_ids

    def test_is_posted_returns_false_when_not_posted(self, extractor):
        """Test that is_posted returns False for new comment IDs."""
        from botocore.exceptions import ClientError
        extractor.s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}},
            "get_object"
        )

        assert extractor.is_posted("new_comment_123") is False

    def test_is_posted_returns_true_for_existing_id(self, extractor):
        """Test that is_posted returns True for existing ID in S3."""
        # Mock S3 response
        mock_body = MagicMock()
        mock_body.read.return_value = b"existing_comment\nother_comment\n"
        extractor.s3_client.get_object.return_value = {"Body": mock_body}

        # Check
        assert extractor.is_posted("existing_comment") is True
        assert extractor.is_posted("new_comment") is False

    def test_add_posted_id(self, extractor):
        """Test adding a posted ID to S3."""
        # Mock empty S3 object
        from botocore.exceptions import ClientError
        extractor.s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}},
            "get_object"
        )

        extractor.add_posted_id("comment_123")

        # Verify put_object was called with correct content
        extractor.s3_client.put_object.assert_called_once()
        call_args = extractor.s3_client.put_object.call_args
        assert call_args[1]['Bucket'] == 'test-bucket'
        assert call_args[1]['Key'] == 'state/posted_ids.txt'
        assert b'comment_123\n' in call_args[1]['Body']

    def test_add_posted_id_appends(self, extractor):
        """Test that adding multiple IDs appends them."""
        # Mock existing S3 content
        mock_body = MagicMock()
        mock_body.read.return_value = b"comment_111\n"
        extractor.s3_client.get_object.return_value = {"Body": mock_body}

        extractor.add_posted_id("comment_222")

        # Verify put_object was called with both IDs
        call_args = extractor.s3_client.put_object.call_args
        body = call_args[1]['Body']
        assert b'comment_111\n' in body
        assert b'comment_222\n' in body

    def test_add_posted_id_does_not_duplicate(self, extractor):
        """Test that adding the same ID twice doesn't create duplicates."""
        # Mock existing S3 content
        mock_body = MagicMock()
        mock_body.read.return_value = b"comment_123\n"
        extractor.s3_client.get_object.return_value = {"Body": mock_body}

        extractor.add_posted_id("comment_123")

        # Verify put_object was not called (ID already exists)
        extractor.s3_client.put_object.assert_not_called()


class TestPostedCommentsExtractorFactory:
    """Test suite for posted comments extractor factory."""

    def test_factory_creates_local_disk_extractor_by_default(self):
        """Test that factory creates LocalDiskPostedExtractor by default."""
        from src.posted_comments_extractor_factory import create_posted_comments_extractor
        
        extractor = create_posted_comments_extractor()
        assert isinstance(extractor, LocalDiskPostedExtractor)

    def test_factory_creates_local_disk_extractor_when_configured(self):
        """Test that factory creates LocalDiskPostedExtractor when POSTED_COMMENTS_STORAGE_TYPE=local."""
        from src.posted_comments_extractor_factory import create_posted_comments_extractor
        
        with patch.dict(os.environ, {'POSTED_COMMENTS_STORAGE_TYPE': 'local'}):
            extractor = create_posted_comments_extractor()
            assert isinstance(extractor, LocalDiskPostedExtractor)

    def test_factory_creates_tigris_extractor_when_configured(self):
        """Test that factory creates TigrisPostedExtractor when POSTED_COMMENTS_STORAGE_TYPE=tigris."""
        from src.posted_comments_extractor_factory import create_posted_comments_extractor
        
        with patch.dict(os.environ, {
            'POSTED_COMMENTS_STORAGE_TYPE': 'tigris',
            'AWS_ACCESS_KEY_ID': 'test_key',
            'AWS_SECRET_ACCESS_KEY': 'test_secret',
            'TIGRIS_BUCKET_NAME': 'test-bucket'
        }):
            with patch('src.base_json_extractor.boto3'):
                extractor = create_posted_comments_extractor()
                assert isinstance(extractor, TigrisPostedExtractor)

    def test_factory_raises_on_invalid_storage_type(self):
        """Test that factory raises ValueError for invalid storage type."""
        from src.posted_comments_extractor_factory import create_posted_comments_extractor
        
        with patch.dict(os.environ, {'POSTED_COMMENTS_STORAGE_TYPE': 'invalid'}):
            with pytest.raises(ValueError, match="Invalid POSTED_COMMENTS_STORAGE_TYPE"):
                create_posted_comments_extractor()
