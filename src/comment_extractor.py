"""
Abstract interface for comment extraction from different storage backends.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class CommentExtractor(ABC):
    """Abstract base class for comment extraction from various storage backends."""

    @abstractmethod
    def load_pending_comments(self) -> List[Dict[str, Any]]:
        """
        Load pending comments from storage.

        Returns:
            List of pending comment dictionaries
        """

    @abstractmethod
    def save_pending_comment(self, comment_data: Dict[str, Any]) -> None:
        """
        Save a single pending comment to storage.

        Args:
            comment_data: Comment data to save
        """

    @abstractmethod
    def clear_pending_comments(self) -> None:
        """Clear all pending comments from storage."""
