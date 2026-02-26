"""
Unit tests for ModeExtractor implementations.

Tests follow TDD approach - tests written before implementation.
"""
import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock, Mock

import pytest

from tests.unit.test_extractor_base import BaseLocalDiskExtractorTests, BaseTigrisExtractorTests


class TestLocalDiskModeExtractor(BaseLocalDiskExtractorTests):
    """Test suite for LocalDiskModeExtractor."""

    @pytest.fixture
    def extractor(self, temp_state_dir):
        """Create a LocalDiskModeExtractor instance."""
        from src.local_disk_mode_extractor import LocalDiskModeExtractor
        return LocalDiskModeExtractor(state_dir=temp_state_dir)

    def test_implements_interface(self, extractor):
        """Test that LocalDiskModeExtractor implements ModeExtractor interface."""
        from src.mode_extractor import ModeExtractor
        assert isinstance(extractor, ModeExtractor)

    def test_get_auto_mode_default_false(self, extractor):
        """Test that get_auto_mode returns False when no file exists."""
        assert extractor.get_auto_mode() is False

    def test_set_then_get_auto_mode_true(self, extractor):
        """Test setting auto_mode to True and reading it back."""
        extractor.set_auto_mode(True)
        assert extractor.get_auto_mode() is True

    def test_set_then_get_auto_mode_false(self, extractor):
        """Test setting auto_mode to False and reading it back."""
        extractor.set_auto_mode(True)
        extractor.set_auto_mode(False)
        assert extractor.get_auto_mode() is False

    def test_persists_to_file(self, extractor, temp_state_dir):
        """Test that mode is persisted to disk."""
        extractor.set_auto_mode(True)
        mode_file = os.path.join(temp_state_dir, "mode.json")
        assert os.path.exists(mode_file)
        with open(mode_file, "r") as f:
            data = json.load(f)
        assert data["auto_mode"] is True

    def test_loads_from_existing_file(self, temp_state_dir):
        """Test that mode is loaded from an existing file."""
        from src.local_disk_mode_extractor import LocalDiskModeExtractor
        mode_file = os.path.join(temp_state_dir, "mode.json")
        with open(mode_file, "w") as f:
            json.dump({"auto_mode": True}, f)
        extractor = LocalDiskModeExtractor(state_dir=temp_state_dir)
        assert extractor.get_auto_mode() is True


class TestTigrismModeExtractor(BaseTigrisExtractorTests):
    """Test suite for TigrisModeExtractor using mocked S3."""

    @pytest.fixture
    def extractor(self, mock_s3_client, monkeypatch):
        """Create a TigrisModeExtractor with mocked S3 client."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
        monkeypatch.setenv("TIGRIS_BUCKET_NAME", "test-bucket")
        from src.tigris_mode_extractor import TigrisModeExtractor
        ext = TigrisModeExtractor()
        ext.s3_client = mock_s3_client
        return ext

    def test_implements_interface(self, extractor):
        """Test that TigrisModeExtractor implements ModeExtractor interface."""
        from src.mode_extractor import ModeExtractor
        assert isinstance(extractor, ModeExtractor)

    def test_get_auto_mode_default_false_when_no_key(self, extractor, mock_s3_client):
        """Test get_auto_mode returns False when S3 object doesn't exist."""
        self.setup_mock_no_such_key(mock_s3_client)
        assert extractor.get_auto_mode() is False

    def test_get_auto_mode_true_from_s3(self, extractor, mock_s3_client):
        """Test get_auto_mode returns True when S3 object has auto_mode=true."""
        self.setup_mock_get_object(mock_s3_client, {"auto_mode": True})
        assert extractor.get_auto_mode() is True

    def test_get_auto_mode_false_from_s3(self, extractor, mock_s3_client):
        """Test get_auto_mode returns False when S3 object has auto_mode=false."""
        self.setup_mock_get_object(mock_s3_client, {"auto_mode": False})
        assert extractor.get_auto_mode() is False

    def test_set_auto_mode_saves_to_s3(self, extractor, mock_s3_client):
        """Test that set_auto_mode saves data to S3."""
        extractor.set_auto_mode(True)
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        saved_data = json.loads(call_kwargs["Body"])
        assert saved_data["auto_mode"] is True

    def test_object_key_is_correct(self, extractor):
        """Test that the S3 object key is correct."""
        assert extractor._get_object_key() == "state/mode.json"


class TestModeExtractorFactory:
    """Test suite for mode extractor factory function."""

    def test_factory_returns_local_by_default(self, monkeypatch):
        """Test factory returns LocalDiskModeExtractor when MODE_STORAGE_TYPE not set."""
        monkeypatch.delenv("MODE_STORAGE_TYPE", raising=False)
        from src.mode_extractor_factory import create_mode_extractor
        from src.local_disk_mode_extractor import LocalDiskModeExtractor
        extractor = create_mode_extractor()
        assert isinstance(extractor, LocalDiskModeExtractor)

    def test_factory_returns_local_explicitly(self, monkeypatch):
        """Test factory returns LocalDiskModeExtractor when MODE_STORAGE_TYPE=local."""
        monkeypatch.setenv("MODE_STORAGE_TYPE", "local")
        from src.mode_extractor_factory import create_mode_extractor
        from src.local_disk_mode_extractor import LocalDiskModeExtractor
        extractor = create_mode_extractor()
        assert isinstance(extractor, LocalDiskModeExtractor)

    def test_factory_returns_tigris(self, monkeypatch):
        """Test factory returns TigrismModeExtractor when MODE_STORAGE_TYPE=tigris."""
        monkeypatch.setenv("MODE_STORAGE_TYPE", "tigris")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
        monkeypatch.setenv("TIGRIS_BUCKET_NAME", "test-bucket")
        from src.mode_extractor_factory import create_mode_extractor
        from src.tigris_mode_extractor import TigrisModeExtractor
        extractor = create_mode_extractor()
        assert isinstance(extractor, TigrisModeExtractor)
