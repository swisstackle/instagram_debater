"""
Instagram Graph API wrapper for the Instagram Debate Bot.
Handles webhook verification, comment fetching, and reply posting.
"""
import hashlib
import hmac
import json
import logging
from typing import Any, Dict, List

import requests

# Configure logging
logger = logging.getLogger(__name__)


class InstagramAPI:
    """Wrapper for Instagram Graph API operations."""

    API_VERSION = "v25.0"
    BASE_URL = f"https://graph.instagram.com/{API_VERSION}"

    def __init__(self, access_token: str, app_secret: str):
        """
        Initialize Instagram API client.

        Args:
            access_token: Instagram access token
            app_secret: Instagram app secret for webhook verification
        """
        self.access_token = access_token
        self.app_secret = app_secret

    def verify_webhook_signature(self, payload: bytes, signature_header: str) -> bool:
        """
        Verify Instagram webhook signature.

        Args:
            payload: Raw request body bytes
            signature_header: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        if not signature_header:
            return False

        # Extract signature from header (format: "sha256=<signature>")
        try:
            method, signature = signature_header.split("=", 1)
            if method != "sha256":
                return False
        except ValueError:
            return False

        # Compute expected signature
        expected_signature = hmac.new(
            self.app_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)

    def get_comment(self, comment_id: str) -> Dict[str, Any]:
        """
        Fetch a comment by ID.

        Args:
            comment_id: Instagram comment ID

        Returns:
            Comment data dictionary
        """
        url = f"{self.BASE_URL}/{comment_id}"
        params = {
            "access_token": self.access_token,
            "fields": "id,text,timestamp,from,media"
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_comment_replies(self, comment_id: str) -> List[Dict[str, Any]]:
        """
        Get all replies to a comment.

        Args:
            comment_id: Instagram comment ID

        Returns:
            List of reply comment dictionaries
        """
        url = f"{self.BASE_URL}/{comment_id}/replies"
        params = {
            "access_token": self.access_token
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    def get_post_caption(self, post_id: str) -> str:
        """
        Get the caption of a post.

        Args:
            post_id: Instagram post/media ID

        Returns:
            Post caption text
        """
        url = f"{self.BASE_URL}/{post_id}"
        params = {
            "access_token": self.access_token,
            "fields": "caption"
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("caption", "")

    def post_reply(self, comment_id: str, message: str) -> Dict[str, Any]:
        """
        Post a reply to a comment.

        Args:
            comment_id: Instagram comment ID to reply to
            message: Reply message text

        Returns:
            Response data with new comment ID
            
        Raises:
            requests.exceptions.HTTPError: If the Graph API returns an error
        """
        url = f"{self.BASE_URL}/{comment_id}/replies"
        params = {
            "access_token": self.access_token,
            "message": message
        }

        try:
            response = requests.post(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Log detailed error information for debugging
            try:
                error_data = e.response.json()
                error_code = error_data.get("error", {}).get("code")
                error_msg = error_data.get("error", {}).get("message", str(e))
                
                if error_code == 190:
                    # OAuthException - token is invalid
                    logger.error(
                        "OAuth token invalid (code 190): %s. "
                        "Token may be expired, revoked, or lack required scopes. Token used: %s",
                        error_msg, self.access_token
                    )
                elif error_code in [104, 100]:
                    # Token/permission issues
                    logger.error(
                        "Graph API permission/token error (code %s): %s",
                        error_code, error_msg
                    )
                else:
                    logger.error(
                        "Graph API error code %s: %s",
                        error_code, error_msg
                    )
                    
                # Log full error body for diagnosis
                logger.debug("Full Graph API error response: %s", json.dumps(error_data, indent=2))
            except (ValueError, KeyError):
                # Could not parse JSON error response
                logger.error(
                    "Graph API HTTP %s error: %s (could not parse error body)",
                    e.response.status_code, e
                )
            
            # Re-raise so caller can handle
            raise
