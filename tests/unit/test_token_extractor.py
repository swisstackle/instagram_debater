"""
Unit tests for token extractor interface.
"""
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

import pytest

from src.token_extractor import TokenExtractor


class ConcreteTokenExtractor(TokenExtractor):
    """Concrete implementation for testing abstract interface."""
    
    def save_token(self, access_token: str, token_type: str = "bearer", 
                   expires_in: int = 5184000, user_id: str = None, username: str = None) -> None:
        """Save token implementation."""
        pass
    
    def get_token(self):
        """Get token implementation."""
        return None
    
    def is_token_expired(self, buffer_days: int = 5) -> bool:
        """Check token expiration implementation."""
        return False
    
    def refresh_token(self, client_secret: str) -> bool:
        """Refresh token implementation."""
        return False
    
    def clear_token(self) -> None:
        """Clear token implementation."""
        pass


class TestTokenExtractor:
    """Test suite for TokenExtractor abstract interface."""

    def test_token_extractor_cannot_be_instantiated(self):
        """Test that TokenExtractor is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            TokenExtractor()

    def test_concrete_implementation_can_be_instantiated(self):
        """Test that concrete implementation of TokenExtractor can be instantiated."""
        extractor = ConcreteTokenExtractor()
        assert extractor is not None

    def test_save_token_signature(self):
        """Test that save_token has correct signature."""
        extractor = ConcreteTokenExtractor()
        # Should not raise
        extractor.save_token("test_token")
        extractor.save_token("test_token", token_type="bearer", expires_in=5184000)
        extractor.save_token("test_token", user_id="12345", username="testuser")

    def test_get_token_signature(self):
        """Test that get_token has correct signature."""
        extractor = ConcreteTokenExtractor()
        result = extractor.get_token()
        assert result is None

    def test_is_token_expired_signature(self):
        """Test that is_token_expired has correct signature."""
        extractor = ConcreteTokenExtractor()
        result = extractor.is_token_expired()
        assert isinstance(result, bool)
        
        result = extractor.is_token_expired(buffer_days=5)
        assert isinstance(result, bool)

    def test_refresh_token_signature(self):
        """Test that refresh_token has correct signature."""
        extractor = ConcreteTokenExtractor()
        result = extractor.refresh_token("secret")
        assert isinstance(result, bool)

    def test_clear_token_signature(self):
        """Test that clear_token has correct signature."""
        extractor = ConcreteTokenExtractor()
        # Should not raise
        extractor.clear_token()

    def test_token_extractor_has_all_required_methods(self):
        """Test that TokenExtractor defines all required methods."""
        required_methods = [
            'save_token',
            'get_token',
            'is_token_expired',
            'refresh_token',
            'clear_token'
        ]
        
        for method in required_methods:
            assert hasattr(TokenExtractor, method)
