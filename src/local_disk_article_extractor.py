"""
Local disk implementation of article storage.

Stores articles as a JSON file on the local filesystem.
Default location: state/articles.json
"""
from typing import Dict, List, Optional

from src.article_extractor import ArticleExtractor
from src.base_json_extractor import BaseLocalDiskExtractor


class LocalDiskArticleExtractor(BaseLocalDiskExtractor, ArticleExtractor):
    """
    Local disk implementation of article storage.

    Stores articles in a JSON file on the local filesystem.
    Default location: state/articles.json
    """

    def _get_filename(self) -> str:
        """Get the filename for article storage."""
        return "articles.json"

    def get_articles(self) -> List[Dict]:
        """
        Get all articles from local disk.

        Returns:
            List of article dicts.
        """
        data = self._load_data({"articles": []})
        return data.get("articles", [])

    def get_article(self, article_id: str) -> Optional[Dict]:
        """
        Get a single article by ID from local disk.

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
        Save (create or update) an article on local disk.

        Args:
            article_id: The unique identifier of the article.
            title: Article title.
            content: Article content (markdown).
            link: URL link to the article.
        """
        data = self._load_data({"articles": []})
        articles = data.get("articles", [])

        article = {"id": article_id, "title": title, "content": content, "link": link}

        for i, existing in enumerate(articles):
            if existing.get("id") == article_id:
                articles[i] = article
                self._save_data({"articles": articles})
                return

        articles.append(article)
        self._save_data({"articles": articles})

    def delete_article(self, article_id: str) -> bool:
        """
        Delete an article by ID from local disk.

        Args:
            article_id: The unique identifier of the article.

        Returns:
            True if deleted, False if not found.
        """
        data = self._load_data({"articles": []})
        articles = data.get("articles", [])
        new_articles = [a for a in articles if a.get("id") != article_id]

        if len(new_articles) == len(articles):
            return False

        self._save_data({"articles": new_articles})
        return True
