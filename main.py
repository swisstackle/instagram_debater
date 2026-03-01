#!/usr/bin/env python
"""
Main entry point for the Instagram Debate Bot.
Run this to process pending comments.
"""
from src.config import Config
from src.instagram_api import InstagramAPI
from src.llm_client import LLMClient
from src.processor import CommentProcessor
from src.account_registry_factory import create_account_registry
from src.token_extractor_factory import create_token_extractor
from src.comment_extractor_factory import create_comment_extractor
from src.audit_log_extractor_factory import create_audit_log_extractor
from src.article_extractor_factory import create_article_extractor
from src.prompt_extractor_factory import create_prompt_extractor


def _run_for_account(config: Config, account_id: str, access_token: str) -> None:
    """Run comment processing for a single Instagram account."""
    instagram_api = InstagramAPI(
        access_token=access_token,
        app_secret=config.instagram_app_secret
    )

    llm_client = LLMClient(
        api_key=config.openrouter_api_key,
        model_name=config.model_name,
        max_tokens=config.max_tokens,
        temperature=config.temperature
    )

    processor = CommentProcessor(
        instagram_api=instagram_api,
        llm_client=llm_client,
        validator=None,
        config=config,
        comment_extractor=create_comment_extractor(account_id=account_id),
        audit_log_extractor=create_audit_log_extractor(account_id=account_id),
        article_extractor=create_article_extractor(account_id=account_id),
        prompt_extractor=create_prompt_extractor(account_id=account_id),
    )

    processor.run()


def main():
    """Main entry point for the bot."""
    config = Config()

    # Multi-account mode: iterate over all registered accounts
    registry = create_account_registry()
    accounts = registry.get_accounts()

    if accounts:
        for account in accounts:
            account_id = account.get("id")
            if not account_id:
                continue
            # Load per-account token
            token_ext = create_token_extractor(account_id=account_id)
            token_data = token_ext.get_token()
            if not token_data:
                continue
            access_token = token_data.get("access_token", "")
            if not access_token:
                continue
            _run_for_account(config, account_id, access_token)
    else:
        # Fallback: single-account mode using Config (env var / legacy token)
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

        processor = CommentProcessor(
            instagram_api=instagram_api,
            llm_client=llm_client,
            validator=None,
            config=config
        )

        processor.run()


if __name__ == "__main__":
    main()
