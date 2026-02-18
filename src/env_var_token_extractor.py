"""
Environment variable token extractor implementation.

Reads Instagram access token directly from environment variables.
This is a read-only implementation with no refresh or persistence capabilities.
"""
import os
from typing import Optional, Dict, Any

from src.token_extractor import TokenExtractor


class EnvVarTokenExtractor(TokenExtractor):
    """Environment variable implementation for token storage."""

    def __init__(self):
        """Initialize the environment variable token extractor."""
        pass

    def save_token(
        self,
        access_token: str,
        token_type: str = "bearer",
        expires_in: int = 5184000,
        user_id: Optional[str] = None,
        username: Optional[str] = None
    ) -> None:
        """
        Save is not supported for environment variable tokens.

        This operation is a no-op since tokens are read from environment.
        """
        pass

    def get_token(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the access token from environment variable.

        Returns:
            Dictionary with access_token key, or None if not set.
        """
        token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        if token:
            return {
                "access_token": token,
                "token_type": "bearer",
                "source": "environment_variable"
            }
        return None

    def is_token_expired(self, buffer_days: int = 5) -> bool:
        """
        Check if token exists from environment variable.

        Environment variable tokens have no expiration tracking,
        so we return False if the token exists (not expired).

        Args:
            buffer_days: Unused for environment variables

        Returns:
            False if token exists, True if missing (treat missing as expired)
        """
        return os.getenv("INSTAGRAM_ACCESS_TOKEN") is None

    def refresh_token(self, client_secret: str) -> bool:
        """
        Refresh is not supported for environment variable tokens.

        Returns:
            False - refresh not supported
        """
        return False

    def clear_token(self) -> None:
        """
        Clear is not supported for environment variable tokens.

        This operation is a no-op since tokens are read from environment.
        """
        pass
