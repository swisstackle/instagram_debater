"""
Unit tests for audit log extractors.
"""
import json
import os
from unittest.mock import patch, Mock

import pytest

from src.audit_log_extractor import AuditLogExtractor
from src.local_disk_audit_extractor import LocalDiskAuditExtractor
from src.tigris_audit_extractor import TigrisAuditExtractor
from tests.unit.test_extractor_base import BaseLocalDiskExtractorTests, BaseTigrisExtractorTests


class TestLocalDiskAuditExtractor(BaseLocalDiskExtractorTests):
    """Test suite for LocalDiskAuditExtractor."""

    @pytest.fixture
    def extractor(self, temp_state_dir):
        """Create a LocalDiskAuditExtractor instance."""
        return LocalDiskAuditExtractor(state_dir=temp_state_dir)

    def test_implements_interface(self, extractor):
        """Test that LocalDiskAuditExtractor implements AuditLogExtractor interface."""
        assert isinstance(extractor, AuditLogExtractor)

    def test_load_entries_file_not_exists(self, extractor):
        """Test loading entries when file doesn't exist."""
        entries = extractor.load_entries()
        assert entries == []

    def test_load_entries_file_exists(self, extractor, temp_state_dir):
        """Test loading entries from existing file."""
        # Create test file
        audit_file = os.path.join(temp_state_dir, "audit_log.json")
        test_data = {
            "version": "1.0",
            "entries": [
                {
                    "id": "log_001",
                    "comment_id": "123",
                    "comment_text": "Test comment 1",
                    "status": "approved"
                },
                {
                    "id": "log_002",
                    "comment_id": "456",
                    "comment_text": "Test comment 2",
                    "status": "pending_review"
                }
            ]
        }
        with open(audit_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        # Load and verify
        entries = extractor.load_entries()
        assert len(entries) == 2
        assert entries[0]["id"] == "log_001"
        assert entries[0]["comment_id"] == "123"
        assert entries[1]["id"] == "log_002"
        assert entries[1]["comment_id"] == "456"

    def test_save_entry_creates_file(self, extractor, temp_state_dir):
        """Test saving an entry creates the file and auto-generates ID."""
        entry_data = {
            "comment_id": "789",
            "post_id": "post_123",
            "username": "testuser",
            "comment_text": "Test comment",
            "generated_response": "Test response",
            "status": "approved",
            "timestamp": "2024-01-15T10:30:00Z"
        }

        extractor.save_entry(entry_data)

        # Verify file was created
        audit_file = os.path.join(temp_state_dir, "audit_log.json")
        assert os.path.exists(audit_file)

        # Verify content
        with open(audit_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert len(data["entries"]) == 1
        assert data["entries"][0]["id"] == "log_001"  # Auto-generated
        assert data["entries"][0]["comment_id"] == "789"
        assert data["entries"][0]["status"] == "approved"

    def test_save_entry_appends_entries(self, extractor, temp_state_dir):
        """Test that saving multiple entries appends them with incrementing IDs."""
        entry1 = {
            "comment_id": "111",
            "comment_text": "Comment 1",
            "status": "approved"
        }
        entry2 = {
            "comment_id": "222",
            "comment_text": "Comment 2",
            "status": "pending_review"
        }
        entry3 = {
            "comment_id": "333",
            "comment_text": "Comment 3",
            "status": "failed"
        }

        extractor.save_entry(entry1)
        extractor.save_entry(entry2)
        extractor.save_entry(entry3)

        # Verify all entries are present with correct IDs
        entries = extractor.load_entries()
        assert len(entries) == 3
        assert entries[0]["id"] == "log_001"
        assert entries[0]["comment_id"] == "111"
        assert entries[1]["id"] == "log_002"
        assert entries[1]["comment_id"] == "222"
        assert entries[2]["id"] == "log_003"
        assert entries[2]["comment_id"] == "333"

    def test_update_entry_existing(self, extractor, temp_state_dir):
        """Test updating an existing entry."""
        # Create initial entry
        entry = {
            "comment_id": "123",
            "comment_text": "Test",
            "status": "pending_review",
            "posted": False
        }
        extractor.save_entry(entry)

        # Update the entry
        updates = {
            "status": "approved",
            "posted": True,
            "posted_at": "2024-01-15T11:00:00Z"
        }
        extractor.update_entry("log_001", updates)

        # Verify update
        entries = extractor.load_entries()
        assert len(entries) == 1
        assert entries[0]["id"] == "log_001"
        assert entries[0]["status"] == "approved"
        assert entries[0]["posted"] is True
        assert entries[0]["posted_at"] == "2024-01-15T11:00:00Z"
        # Original fields should still exist
        assert entries[0]["comment_id"] == "123"

    def test_update_entry_nonexistent(self, extractor):
        """Test updating a non-existent entry (should not raise error)."""
        updates = {"status": "approved"}
        extractor.update_entry("log_999", updates)  # Should not raise

    def test_update_entry_file_not_exists(self, extractor):
        """Test updating when file doesn't exist (should not raise error)."""
        updates = {"status": "approved"}
        extractor.update_entry("log_001", updates)  # Should not raise


class TestTigrisAuditExtractor(BaseTigrisExtractorTests):
    """Test suite for TigrisAuditExtractor."""

    @pytest.fixture
    def extractor(self, mock_s3_client):
        """Create a TigrisAuditExtractor instance with mocked S3 client."""
        with patch('src.base_json_extractor.boto3') as mock_boto3:
            mock_boto3.client.return_value = mock_s3_client
            extractor = TigrisAuditExtractor(
                access_key_id="test_key",
                secret_access_key="test_secret",
                endpoint_url="https://fly.storage.tigris.dev",
                bucket_name="test-bucket",
                region="auto"
            )
            extractor.s3_client = mock_s3_client
            return extractor

    def test_implements_interface(self, extractor):
        """Test that TigrisAuditExtractor implements AuditLogExtractor interface."""
        assert isinstance(extractor, AuditLogExtractor)

    def test_load_entries_object_exists(self, extractor, mock_s3_client):
        """Test loading entries when S3 object exists."""
        test_data = {
            "version": "1.0",
            "entries": [
                {
                    "id": "log_001",
                    "comment_id": "123",
                    "comment_text": "Test comment 1",
                    "status": "approved"
                },
                {
                    "id": "log_002",
                    "comment_id": "456",
                    "comment_text": "Test comment 2",
                    "status": "pending_review"
                }
            ]
        }
        self.setup_mock_get_object(mock_s3_client, test_data)

        entries = extractor.load_entries()

        assert len(entries) == 2
        assert entries[0]["id"] == "log_001"
        assert entries[0]["comment_id"] == "123"
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="state/audit_log.json"
        )

    def test_load_entries_object_not_exists(self, extractor, mock_s3_client):
        """Test loading entries when S3 object doesn't exist."""
        self.setup_mock_no_such_key(mock_s3_client)

        entries = extractor.load_entries()

        assert entries == []

    def test_save_entry_creates_object(self, extractor, mock_s3_client):
        """Test saving an entry creates the S3 object with auto-generated ID."""
        # Setup: object doesn't exist initially
        self.setup_mock_no_such_key(mock_s3_client)

        entry_data = {
            "comment_id": "789",
            "post_id": "post_123",
            "username": "testuser",
            "comment_text": "Test comment",
            "generated_response": "Test response",
            "status": "approved",
            "timestamp": "2024-01-15T10:30:00Z"
        }

        extractor.save_entry(entry_data)

        # Verify put_object was called
        assert mock_s3_client.put_object.called
        call_args = mock_s3_client.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert call_args[1]["Key"] == "state/audit_log.json"
        assert call_args[1]["ContentType"] == "application/json"
        
        # Verify the body contains our entry with auto-generated ID
        body_data = json.loads(call_args[1]["Body"])
        assert body_data["version"] == "1.0"
        assert len(body_data["entries"]) == 1
        assert body_data["entries"][0]["id"] == "log_001"
        assert body_data["entries"][0]["comment_id"] == "789"

    def test_save_entry_appends_entries(self, extractor, mock_s3_client):
        """Test that saving multiple entries appends them with incrementing IDs."""
        # Setup: object exists with one entry
        existing_data = {
            "version": "1.0",
            "entries": [
                {"id": "log_001", "comment_id": "111", "status": "approved"}
            ]
        }
        self.setup_mock_get_object(mock_s3_client, existing_data)

        new_entry = {
            "comment_id": "222",
            "comment_text": "New comment",
            "status": "pending_review"
        }
        extractor.save_entry(new_entry)

        # Verify put_object was called with both entries
        call_args = mock_s3_client.put_object.call_args
        body_data = json.loads(call_args[1]["Body"])
        assert len(body_data["entries"]) == 2
        assert body_data["entries"][0]["id"] == "log_001"
        assert body_data["entries"][0]["comment_id"] == "111"
        assert body_data["entries"][1]["id"] == "log_002"
        assert body_data["entries"][1]["comment_id"] == "222"

    def test_update_entry_existing(self, extractor, mock_s3_client):
        """Test updating an existing entry in S3."""
        # Setup: object exists with entry to update
        existing_data = {
            "version": "1.0",
            "entries": [
                {
                    "id": "log_001",
                    "comment_id": "123",
                    "status": "pending_review",
                    "posted": False
                }
            ]
        }
        self.setup_mock_get_object(mock_s3_client, existing_data)

        updates = {
            "status": "approved",
            "posted": True,
            "posted_at": "2024-01-15T11:00:00Z"
        }
        extractor.update_entry("log_001", updates)

        # Verify put_object was called with updated entry
        call_args = mock_s3_client.put_object.call_args
        body_data = json.loads(call_args[1]["Body"])
        assert len(body_data["entries"]) == 1
        assert body_data["entries"][0]["id"] == "log_001"
        assert body_data["entries"][0]["status"] == "approved"
        assert body_data["entries"][0]["posted"] is True
        assert body_data["entries"][0]["posted_at"] == "2024-01-15T11:00:00Z"

    def test_update_entry_nonexistent(self, extractor, mock_s3_client):
        """Test updating a non-existent entry (should not raise error)."""
        existing_data = {
            "version": "1.0",
            "entries": [{"id": "log_001", "comment_id": "123"}]
        }
        self.setup_mock_get_object(mock_s3_client, existing_data)

        updates = {"status": "approved"}
        extractor.update_entry("log_999", updates)  # Should not raise

        # Verify put_object was still called (data unchanged)
        assert mock_s3_client.put_object.called

    def test_update_entry_object_not_exists(self, extractor, mock_s3_client):
        """Test updating when S3 object doesn't exist (should not raise error)."""
        self.setup_mock_no_such_key(mock_s3_client)

        updates = {"status": "approved"}
        extractor.update_entry("log_001", updates)  # Should not raise

    def test_initialization_with_env_vars(self):
        """Test TigrisAuditExtractor initialization from environment variables."""
        with patch.dict(os.environ, {
            'AWS_ACCESS_KEY_ID': 'env_key',
            'AWS_SECRET_ACCESS_KEY': 'env_secret',
            'AWS_ENDPOINT_URL_S3': 'https://env.endpoint.com',
            'TIGRIS_BUCKET_NAME': 'env-bucket',
            'AWS_REGION': 'env-region'
        }):
            with patch('src.base_json_extractor.boto3') as mock_boto3:
                extractor = TigrisAuditExtractor()
                
                # Verify boto3 client was initialized with correct params
                mock_boto3.client.assert_called_once()
                call_kwargs = mock_boto3.client.call_args[1]
                assert call_kwargs['aws_access_key_id'] == 'env_key'
                assert call_kwargs['aws_secret_access_key'] == 'env_secret'
                assert call_kwargs['endpoint_url'] == 'https://env.endpoint.com'
                assert call_kwargs['region_name'] == 'env-region'


class TestAuditLogExtractorFactory:
    """Test suite for audit log extractor factory function."""

    def test_create_local_disk_extractor(self):
        """Test creating local disk extractor via factory."""
        from src.audit_log_extractor_factory import create_audit_log_extractor
        
        with patch.dict(os.environ, {'AUDIT_LOG_STORAGE_TYPE': 'local'}):
            extractor = create_audit_log_extractor()
            assert isinstance(extractor, LocalDiskAuditExtractor)

    def test_create_tigris_extractor(self):
        """Test creating Tigris extractor via factory."""
        from src.audit_log_extractor_factory import create_audit_log_extractor
        
        with patch.dict(os.environ, {
            'AUDIT_LOG_STORAGE_TYPE': 'tigris',
            'AWS_ACCESS_KEY_ID': 'test_key',
            'AWS_SECRET_ACCESS_KEY': 'test_secret',
            'AWS_ENDPOINT_URL_S3': 'https://test.endpoint.com',
            'TIGRIS_BUCKET_NAME': 'test-bucket',
            'AWS_REGION': 'auto'
        }):
            with patch('src.base_json_extractor.boto3'):
                extractor = create_audit_log_extractor()
                assert isinstance(extractor, TigrisAuditExtractor)

    def test_default_to_local_disk(self):
        """Test that factory defaults to local disk when no type specified."""
        from src.audit_log_extractor_factory import create_audit_log_extractor
        
        with patch.dict(os.environ, {}, clear=True):
            extractor = create_audit_log_extractor()
            assert isinstance(extractor, LocalDiskAuditExtractor)

    def test_case_insensitive_storage_type(self):
        """Test that storage type is case-insensitive."""
        from src.audit_log_extractor_factory import create_audit_log_extractor
        
        with patch.dict(os.environ, {'AUDIT_LOG_STORAGE_TYPE': 'LOCAL'}):
            extractor = create_audit_log_extractor()
            assert isinstance(extractor, LocalDiskAuditExtractor)
