"""
Unit tests for token extractor factory.
"""
import pytest

from src.token_extractor_factory import create_token_extractor
from src.local_disk_token_extractor import LocalDiskTokenExtractor
from src.tigris_token_extractor import TigrisTokenExtractor


class TestTokenExtractorFactory:
    """Test suite for token extractor factory."""

    def test_factory_returns_local_by_default(self, monkeypatch):
        """Test that factory returns LocalDiskTokenExtractor by default."""
        monkeypatch.delenv('OAUTH_TOKEN_STORAGE_TYPE', raising=False)
        
        extractor = create_token_extractor()
        
        assert isinstance(extractor, LocalDiskTokenExtractor)

    def test_factory_returns_local_when_explicit(self, monkeypatch):
        """Test that factory returns LocalDiskTokenExtractor when explicitly set."""
        monkeypatch.setenv('OAUTH_TOKEN_STORAGE_TYPE', 'local')
        
        extractor = create_token_extractor()
        
        assert isinstance(extractor, LocalDiskTokenExtractor)

    def test_factory_returns_tigris_when_set(self, monkeypatch):
        """Test that factory returns TigrisTokenExtractor when set."""
        monkeypatch.setenv('OAUTH_TOKEN_STORAGE_TYPE', 'tigris')
        monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'test_key')
        monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'test_secret')
        monkeypatch.setenv('TIGRIS_BUCKET_NAME', 'test_bucket')
        
        extractor = create_token_extractor()
        
        assert isinstance(extractor, TigrisTokenExtractor)

    def test_factory_accepts_state_dir_parameter(self, monkeypatch):
        """Test that factory accepts state_dir parameter."""
        monkeypatch.delenv('OAUTH_TOKEN_STORAGE_TYPE', raising=False)
        
        extractor = create_token_extractor(state_dir="/custom/state")
        
        assert isinstance(extractor, LocalDiskTokenExtractor)
        # Verify state_dir was passed
        assert extractor.state_dir == "/custom/state"

    def test_factory_case_insensitive_local(self, monkeypatch):
        """Test that factory is case-insensitive for 'local'."""
        monkeypatch.setenv('OAUTH_TOKEN_STORAGE_TYPE', 'LOCAL')
        
        extractor = create_token_extractor()
        
        assert isinstance(extractor, LocalDiskTokenExtractor)

    def test_factory_case_insensitive_tigris(self, monkeypatch):
        """Test that factory is case-insensitive for 'tigris'."""
        monkeypatch.setenv('OAUTH_TOKEN_STORAGE_TYPE', 'TIGRIS')
        monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'test_key')
        monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'test_secret')
        monkeypatch.setenv('TIGRIS_BUCKET_NAME', 'test_bucket')
        
        extractor = create_token_extractor()
        
        assert isinstance(extractor, TigrisTokenExtractor)

    def test_factory_defaults_to_local_for_unknown_type(self, monkeypatch):
        """Test that factory defaults to local for unknown storage type."""
        monkeypatch.setenv('OAUTH_TOKEN_STORAGE_TYPE', 'unknown')
        
        extractor = create_token_extractor()
        
        assert isinstance(extractor, LocalDiskTokenExtractor)
