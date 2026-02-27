"""
Abstract interface for article storage backends.

Defines the interface for getting, saving, and deleting articles.
Implementations can store articles locally or in distributed storage (Tigris/S3),
allowing all components to share the same article data.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class ArticleExtractor(ABC):
    """Abstract base class for article storage backends."""

    @abstractmethod
    def get_articles(self) -> List[Dict]:
        """
        Get all articles.

        Returns:
            List of article dicts with id, title, content, and link keys.
        """

    @abstractmethod
    def get_article(self, article_id: str) -> Optional[Dict]:
        """
        Get a single article by ID.

        Args:
            article_id: The unique identifier of the article.

        Returns:
            Article dict with id, title, content, and link keys, or None if not found.
        """

    @abstractmethod
    def save_article(self, article_id: str, title: str, content: str, link: str) -> None:
        """
        Save (create or update) an article.

        Args:
            article_id: The unique identifier of the article.
            title: Article title.
            content: Article content (markdown).
            link: URL link to the article.
        """

    @abstractmethod
    def delete_article(self, article_id: str) -> bool:
        """
        Delete an article by ID.

        Args:
            article_id: The unique identifier of the article.

        Returns:
            True if the article was deleted, False if it was not found.
        """
