"""
Local disk implementation of comment extractor.
"""
from typing import Any, Dict, List

from src.comment_extractor import CommentExtractor
from src.base_json_extractor import BaseLocalDiskExtractor


class LocalDiskExtractor(BaseLocalDiskExtractor, CommentExtractor):
    """Comment extractor that uses local disk storage."""

    def _get_filename(self) -> str:
        """Get the filename for comment storage."""
        return "pending_comments.json"

    def load_pending_comments(self) -> List[Dict[str, Any]]:
        """
        Load pending comments from local JSON file.

        Returns:
            List of pending comment dictionaries
        """
        data = self._load_data({"version": "1.0", "comments": []})
        return data.get("comments", [])

    def save_pending_comment(self, comment_data: Dict[str, Any]) -> None:
        """
        Save a single pending comment to local JSON file.

        Args:
            comment_data: Comment data to save
        """
        # Load existing data
        data = self._load_data({"version": "1.0", "comments": []})
        
        # Append new comment
        data["comments"].append(comment_data)
        
        # Save back
        self._save_data(data, ensure_dir=False)

    def clear_pending_comments(self) -> None:
        """Clear all pending comments from local storage."""
        self._save_data(
            {"version": "1.0", "comments": []},
            ensure_dir=False
        )
