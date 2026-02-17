"""
Local disk token extractor implementation.

Stores Instagram OAuth tokens in local file system.
"""
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import requests

from src.token_extractor import TokenExtractor
from src.base_json_extractor import BaseLocalDiskExtractor


class LocalDiskTokenExtractor(BaseLocalDiskExtractor, TokenExtractor):
    """Local disk implementation for OAuth token storage."""

    def __init__(self, state_dir: str = "state"):
        """
        Initialize the local disk token extractor.

        Args:
            state_dir: Directory to store token files (default: "state")
        """
        super().__init__(state_dir=state_dir)

    def _get_filename(self) -> str:
        """Get the filename for token storage."""
        return "instagram_token.json"

    def save_token(
        self,
        access_token: str,
        token_type: str = "bearer",
        expires_in: int = 5184000,
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
        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Prepare token data
        token_data = {
            "access_token": access_token,
            "token_type": token_type,
            "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
            "saved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

        if user_id:
            token_data["user_id"] = user_id
        if username:
            token_data["username"] = username

        # Save to file using inherited method
        self._save_data(token_data, ensure_dir=True)

    def get_token(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the stored access token with metadata.

        Returns:
            Dictionary containing token data, or None if no token is stored.
        """
        try:
            return self._load_data(default_data=None)
        except Exception:  # pylint: disable=broad-exception-caught
            return None

    def is_token_expired(self, buffer_days: int = 5) -> bool:
        """
        Check if the stored token is expired or will expire soon.

        Args:
            buffer_days: Days before expiration to consider token as expired (default: 5)

        Returns:
            True if token is expired, missing, or will expire within buffer_days
            False if token is valid
        """
        token_data = self.get_token()
        if not token_data:
            return True

        try:
            expires_at = datetime.fromisoformat(
                token_data["expires_at"].replace('Z', '+00:00')
            )
            now = datetime.now(timezone.utc)
            buffer_time = timedelta(days=buffer_days)

            # Token is expired if it expires within buffer period
            return expires_at <= (now + buffer_time)
        except (KeyError, ValueError):
            return True

    def refresh_token(self, client_secret: str) -> bool:
        """
        Refresh the long-lived access token using Instagram Graph API.

        Args:
            client_secret: Facebook App Secret for authentication

        Returns:
            True if refresh was successful, False otherwise
        """
        token_data = self.get_token()
        if not token_data:
            return False

        current_token = token_data.get("access_token")
        if not current_token:
            return False

        try:
            # Call Instagram Graph API to refresh token
            response = requests.get(
                'https://graph.instagram.com/refresh_access_token',
                params={
                    'grant_type': 'ig_refresh_token',
                    'access_token': current_token
                },
                timeout=30
            )

            if response.status_code == 200:
                refresh_data = response.json()

                # Save the new token
                self.save_token(
                    access_token=refresh_data.get('access_token'),
                    token_type=refresh_data.get('token_type', 'bearer'),
                    expires_in=refresh_data.get('expires_in', 5184000),
                    user_id=token_data.get('user_id'),
                    username=token_data.get('username')
                )
                return True

            return False
        except (requests.RequestException, KeyError, json.JSONDecodeError):
            return False

    def clear_token(self) -> None:
        """
        Remove the stored token file.
        Used during logout or when token is invalidated.
        """
        try:
            filepath = os.path.join(self.state_dir, self._get_filename())
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:  # pylint: disable=broad-exception-caught
            pass
