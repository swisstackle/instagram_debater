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

    # print all the config variables:
    print(f"Instagram App Secret: {config.instagram_app_secret}")
    print(f"Instagram Access Token: {config.instagram_access_token}")
    print(f"Instagram Verify Token: {config.instagram_verify_token}")
    print(f"Webhook Host: {config.webhook_host}")
    print(f"Webhook Port: {config.webhook_port}")
    print(f"Webhook URL: http://{config.webhook_host}:{config.webhook_port}")
    

   

    # Run uvicorn server
    uvicorn.run(
        app,
        host=config.webhook_host,
        port=config.webhook_port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
