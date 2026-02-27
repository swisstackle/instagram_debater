"""
Factory function for creating article extractors.
"""
import os

from src.article_extractor import ArticleExtractor
from src.local_disk_article_extractor import LocalDiskArticleExtractor
from src.tigris_article_extractor import TigrisArticleExtractor


def create_article_extractor(state_dir: str = "state") -> ArticleExtractor:
    """
    Create an article extractor based on environment configuration.

    Reads the ARTICLE_STORAGE_TYPE environment variable to determine
    which implementation to use:
    - 'local' or unset: LocalDiskArticleExtractor (default)
    - 'tigris': TigrisArticleExtractor

    Args:
        state_dir: Directory for local disk storage (default: "state")

    Returns:
        ArticleExtractor: Configured article extractor instance
    """
    storage_type = os.getenv('ARTICLE_STORAGE_TYPE', 'local').lower()

    if storage_type == 'tigris':
        return TigrisArticleExtractor()
    else:
        # Default to local disk storage
        return LocalDiskArticleExtractor(state_dir=state_dir)
