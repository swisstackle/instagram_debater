#!/usr/bin/env python
"""
Main entry point for the Instagram Debate Bot.
Run this to process pending comments.
"""
from src.config import Config
from src.instagram_api import InstagramAPI
from src.llm_client import LLMClient
from src.validator import ResponseValidator
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

    # Handle multi-article vs single-article mode
    articles_config = config.articles_config

    if len(articles_config) > 1:
        # Multi-article mode: processor handles validation internally
        validator = None
    elif len(articles_config) == 1:
        # Single-article mode: create validator for backward compatibility
        with open(articles_config[0]["path"], 'r', encoding='utf-8') as f:
            article_text = f.read()
        validator = ResponseValidator(article_text)
    else:
        # No articles configured: create a minimal validator
        validator = None

    # Create processor
    processor = CommentProcessor(
        instagram_api=instagram_api,
        llm_client=llm_client,
        validator=validator,
        config=config
    )

    # Run processing
    processor.run()


if __name__ == "__main__":
    main()
