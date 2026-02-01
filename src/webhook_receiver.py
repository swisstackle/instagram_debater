"""
Webhook receiver for Instagram comment notifications.
Handles webhook verification and incoming comment data.
"""
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, Response, Query, HTTPException

from src.file_utils import load_json_file, save_json_file, get_utc_timestamp


app = FastAPI()

# Global webhook receiver instance (will be initialized with config)
_webhook_receiver = None  # pylint: disable=invalid-name


def init_webhook_receiver(verify_token: str, app_secret: str):
    """Initialize the global webhook receiver instance."""
    global _webhook_receiver  # pylint: disable=global-statement
    _webhook_receiver = WebhookReceiver(verify_token, app_secret)


class WebhookReceiver:
    """Handles Instagram webhook events."""

    def __init__(self, verify_token: str, app_secret: str):
        """
        Initialize webhook receiver.

        Args:
            verify_token: Token for webhook verification
            app_secret: App secret for signature verification
        """
        self.verify_token = verify_token
        self.app_secret = app_secret

    def verify_challenge(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook subscription challenge.

        Args:
            mode: hub.mode parameter
            token: hub.verify_token parameter
            challenge: hub.challenge parameter

        Returns:
            Challenge string if valid, None otherwise
        """
        if mode == "subscribe" and token == self.verify_token:
            return challenge
        return None

    def process_webhook_payload(self, payload: Dict[str, Any]) -> None:
        """
        Process incoming webhook payload.

        Args:
            payload: Webhook payload dictionary
        """
        if payload.get("object") != "instagram":
            return

        entries = payload.get("entry", [])
        for entry in entries:
            comment_data = self.extract_comment_data(entry)
            if comment_data:
                self.save_pending_comment(comment_data)

    def extract_comment_data(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract comment data from webhook entry.

        Args:
            entry: Webhook entry dictionary

        Returns:
            Comment data dictionary or None
        """
        changes = entry.get("changes", [])
        for change in changes:
            if change.get("field") == "comments":
                value = change.get("value", {})

                # Extract comment data
                comment_data = {
                    "comment_id": value.get("id"),
                    "post_id": value.get("media", {}).get("id"),
                    "username": value.get("from", {}).get("username"),
                    "user_id": value.get("from", {}).get("id"),
                    "text": value.get("text"),
                    "timestamp": get_utc_timestamp(),
                    "received_at": get_utc_timestamp()
                }
                return comment_data

        return None

    def save_pending_comment(self, comment_data: Dict[str, Any]) -> None:
        """
        Save comment to pending_comments.json.

        Args:
            comment_data: Comment data to save
        """
        # Ensure state directory exists
        state_dir = "state"
        os.makedirs(state_dir, exist_ok=True)

        pending_file = os.path.join(state_dir, "pending_comments.json")

        # Load existing data and add new comment
        data = load_json_file(pending_file, {"version": "1.0", "comments": []})
        data["comments"].append(comment_data)

        # Save back
        save_json_file(pending_file, data)


@app.get("/webhook/instagram")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge")
) -> Response:
    """
    Webhook verification endpoint for Instagram.

    Args:
        hub_mode: Verification mode
        hub_verify_token: Verification token
        hub_challenge: Challenge string to return

    Returns:
        Challenge string or 403 Forbidden
    """
    if _webhook_receiver is None:
        raise HTTPException(status_code=500, detail="Webhook receiver not initialized")

    challenge = _webhook_receiver.verify_challenge(hub_mode, hub_verify_token, hub_challenge)
    if challenge:
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Forbidden")


@app.post("/webhook/instagram")
async def receive_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook receiver endpoint for Instagram comment notifications.

    Args:
        request: FastAPI request object

    Returns:
        Success response
    """
    if _webhook_receiver is None:
        raise HTTPException(status_code=500, detail="Webhook receiver not initialized")

    # Get request body
    body = await request.body()
    payload = await request.json()

    # Verify signature for security
    signature = request.headers.get("X-Hub-Signature-256")
    if signature:
        from src.instagram_api import InstagramAPI  # pylint: disable=import-outside-toplevel
        api = InstagramAPI(access_token="", app_secret=_webhook_receiver.app_secret)
        if not api.verify_webhook_signature(body, signature):
            raise HTTPException(status_code=403, detail="Invalid signature")

    # Process webhook payload
    _webhook_receiver.process_webhook_payload(payload)

    return {"status": "ok"}
