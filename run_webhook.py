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
    print(f"Listening on http://{config.webhook_host}:{config.webhook_port}")

    # Run uvicorn server
    uvicorn.run(
        app,
        host=config.webhook_host,
        port=config.webhook_port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
