"""
Instagram Graph API wrapper for the Instagram Debate Bot.
Handles webhook verification, comment fetching, and reply posting.
"""
from typing import Dict, Any, List, Optional
import hmac
import hashlib
import requests


class InstagramAPI:
    """Wrapper for Instagram Graph API operations."""
    
    API_VERSION = "v18.0"
    BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
    
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
        
        response = requests.get(url, params=params)
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
        
        response = requests.get(url, params=params)
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
        
        response = requests.get(url, params=params)
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
        """
        url = f"{self.BASE_URL}/{comment_id}/replies"
        params = {
            "access_token": self.access_token,
            "message": message
        }
        
        response = requests.post(url, params=params)
        response.raise_for_status()
        return response.json()
