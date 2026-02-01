#!/usr/bin/env python
"""
Run the webhook server for receiving Instagram notifications.
"""
import uvicorn
from src.webhook_receiver import app, init_webhook_receiver
from src.config import Config


def main():
    """Run the webhook server."""
    # Load configuration
    config = Config()

    # Initialize webhook receiver
    init_webhook_receiver(
        verify_token=config.instagram_verify_token,
        app_secret=config.instagram_app_secret
    )

    print("Starting webhook server...")
    print(f"Webhook verification token: {config.instagram_verify_token}")

    # Run uvicorn server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    main()
