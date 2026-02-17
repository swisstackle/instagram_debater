"""
Abstract base class for token extractors.

Defines the interface for storing and retrieving Instagram OAuth tokens.
Implementations can store tokens locally or in distributed storage (Tigris/S3).
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class TokenExtractor(ABC):
    """Abstract base class for token storage backends."""

    @abstractmethod
    def save_token(
        self,
        access_token: str,
        token_type: str = "bearer",
        expires_in: int = 5184000,  # 60 days in seconds
        user_id: Optional[str] = None,
        username: Optional[str] = None
    ) -> None:
        """
        Save an access token with expiration metadata.

        Args:
            access_token: The access token string
            token_type: Token type (default: "bearer")
            expires_in: Token validity in seconds (default: 5184000 = 60 days)
            user_id: Instagram user ID (optional)
            username: Instagram username (optional)
        """

    @abstractmethod
    def get_token(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the stored access token with metadata.

        Returns:
            Dictionary containing token data with keys like access_token, expires_at, etc.
            Returns None if no token is stored.
        """

    @abstractmethod
    def is_token_expired(self, buffer_days: int = 5) -> bool:
        """
        Check if the stored token is expired or will expire soon.

        Args:
            buffer_days: Days before expiration to consider token as expired (default: 5)
                        This allows for proactive refresh.

        Returns:
            True if token is expired, missing, or will expire within buffer_days
            False if token is valid
        """

    @abstractmethod
    def refresh_token(self, client_secret: str) -> bool:
        """
        Refresh the long-lived access token using Instagram Graph API.

        Args:
            client_secret: Facebook App Secret for authentication

        Returns:
            True if refresh was successful, False otherwise
        """

    @abstractmethod
    def clear_token(self) -> None:
        """
        Remove the stored token.
        Used during logout or when token is invalidated.
        """
