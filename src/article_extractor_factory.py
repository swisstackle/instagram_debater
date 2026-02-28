"""
Factory function for creating article extractors.
"""
import os
from typing import Optional

from src.article_extractor import ArticleExtractor
from src.local_disk_article_extractor import LocalDiskArticleExtractor
from src.tigris_article_extractor import TigrisArticleExtractor


def create_article_extractor(state_dir: str = "state", account_id: Optional[str] = None) -> ArticleExtractor:
    """
    Create an article extractor based on environment configuration.

    Reads the ARTICLE_STORAGE_TYPE environment variable to determine
    which implementation to use:
    - 'local' or unset: LocalDiskArticleExtractor (default)
    - 'tigris': TigrisArticleExtractor

    Args:
        state_dir: Directory for local disk storage (default: "state")
        account_id: Optional Instagram account ID for per-account namespacing.
            When provided, storage is scoped to state/accounts/{account_id}/.

    Returns:
        ArticleExtractor: Configured article extractor instance
    """
    storage_type = os.getenv('ARTICLE_STORAGE_TYPE', 'local').lower()

    if storage_type == 'tigris':
        return TigrisArticleExtractor(account_id=account_id)
    else:
        # Default to local disk storage
        if account_id:
            state_dir = os.path.join(state_dir, "accounts", account_id)
        return LocalDiskArticleExtractor(state_dir=state_dir)
