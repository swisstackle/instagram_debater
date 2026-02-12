#!/usr/bin/env python
"""
Main entry point for the Instagram Debate Bot.
Run this to process pending comments.
"""
from src.config import Config
from src.instagram_api import InstagramAPI
from src.llm_client import LLMClient
from src.processor import CommentProcessor


def main():
    """Main entry point for the bot."""
    # Load configuration
    config = Config()

    # Initialize components
    instagram_api = InstagramAPI(
        access_token=config.instagram_access_token,
        app_secret=config.instagram_app_secret
    )

    llm_client = LLMClient(
        api_key=config.openrouter_api_key,
        model_name=config.model_name,
        max_tokens=config.max_tokens,
        temperature=config.temperature
    )

    # Create processor (processor handles validation internally for all modes)
    processor = CommentProcessor(
        instagram_api=instagram_api,
        llm_client=llm_client,
        validator=None,
        config=config
    )

    # Run processing
    processor.run()


if __name__ == "__main__":
    main()
