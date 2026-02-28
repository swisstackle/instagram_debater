"""
Tigris/S3-compatible storage implementation of article storage.

Stores articles in an S3-compatible object storage service,
allowing all distributed components to share the same article data.
Default object key: state/articles.json
"""
from typing import Dict, List, Optional

from src.article_extractor import ArticleExtractor
from src.base_json_extractor import BaseTigrisExtractor


class TigrisArticleExtractor(BaseTigrisExtractor, ArticleExtractor):
    """
    Tigris/S3-compatible storage implementation of article storage.

    Stores articles in an S3-compatible object storage service.
    Default object key: state/articles.json
    """

    def __init__(self, account_id: Optional[str] = None, **kwargs):
        """
        Initialize the Tigris article extractor.

        Args:
            account_id: Optional Instagram account ID for per-account namespacing.
            **kwargs: Additional keyword arguments passed to BaseTigrisExtractor.
        """
        super().__init__(**kwargs)
        self.account_id = account_id

    def _get_object_key(self) -> str:
        """Get the S3 object key for article storage."""
        if self.account_id:
            return f"state/accounts/{self.account_id}/articles.json"
        return "state/articles.json"

    def get_articles(self) -> List[Dict]:
        """
        Get all articles from S3.

        Returns:
            List of article dicts.
        """
        data = self._load_from_s3()
        if data is None:
            return []
        return data.get("articles", [])

    def get_article(self, article_id: str) -> Optional[Dict]:
        """
        Get a single article by ID from S3.

        Args:
            article_id: The unique identifier of the article.

        Returns:
            Article dict or None if not found.
        """
        articles = self.get_articles()
        for article in articles:
            if article.get("id") == article_id:
                return article
        return None

    def save_article(self, article_id: str, title: str, content: str, link: str) -> None:
        """
        Save (create or update) an article in S3.

        Args:
            article_id: The unique identifier of the article.
            title: Article title.
            content: Article content (markdown).
            link: URL link to the article.
        """
        data = self._load_from_s3()
        articles = data.get("articles", []) if data else []

        article = {"id": article_id, "title": title, "content": content, "link": link}

        for i, existing in enumerate(articles):
            if existing.get("id") == article_id:
                articles[i] = article
                self._save_to_s3({"articles": articles})
                return

        articles.append(article)
        self._save_to_s3({"articles": articles})

    def delete_article(self, article_id: str) -> bool:
        """
        Delete an article by ID from S3.

        Args:
            article_id: The unique identifier of the article.

        Returns:
            True if deleted, False if not found.
        """
        data = self._load_from_s3()
        articles = data.get("articles", []) if data else []
        new_articles = [a for a in articles if a.get("id") != article_id]

        if len(new_articles) == len(articles):
            return False

        self._save_to_s3({"articles": new_articles})
        return True
