"""
Token management for Instagram OAuth long-lived access tokens.
Handles storage, retrieval, expiration checking, and refresh of tokens.
"""
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import requests


class TokenManager:
    """
    Manages Instagram OAuth tokens including storage, retrieval, and refresh.
    
    Tokens are stored in a JSON file with expiration metadata.
    Long-lived tokens are valid for 60 days and should be refreshed 5-10 days before expiration.
    """

    def __init__(self, state_dir: str = "state"):
        """
        Initialize the TokenManager.

        Args:
            state_dir: Directory to store token files (default: "state")
        """
        self.state_dir = state_dir
        self.token_file = os.path.join(state_dir, "instagram_token.json")

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
        # Create state directory if it doesn't exist
        os.makedirs(self.state_dir, exist_ok=True)
        
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
        
        # Save to file
        with open(self.token_file, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, indent=2)

    def get_token(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the stored access token with metadata.

        Returns:
            Dictionary containing token data:
                - access_token: The token string
                - token_type: Token type
                - expires_at: ISO 8601 expiration timestamp
                - user_id: Instagram user ID (if available)
                - username: Instagram username (if available)
            Returns None if no token is stored or file doesn't exist.
        """
        if not os.path.exists(self.token_file):
            return None
        
        try:
            with open(self.token_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

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
        if os.path.exists(self.token_file):
            os.remove(self.token_file)
