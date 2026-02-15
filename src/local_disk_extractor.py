"""
Local disk implementation of comment extractor.
"""
import os
from typing import Any, Dict, List

from src.comment_extractor import CommentExtractor
from src.file_utils import load_json_file, save_json_file


class LocalDiskExtractor(CommentExtractor):
    """Comment extractor that uses local disk storage."""

    def __init__(self, state_dir: str = "state"):
        """
        Initialize local disk extractor.

        Args:
            state_dir: Directory for state files (default: "state")
        """
        self.state_dir = state_dir
        os.makedirs(self.state_dir, exist_ok=True)

    def load_pending_comments(self) -> List[Dict[str, Any]]:
        """
        Load pending comments from local JSON file.

        Returns:
            List of pending comment dictionaries
        """
        pending_file = os.path.join(self.state_dir, "pending_comments.json")
        data = load_json_file(pending_file, {"version": "1.0", "comments": []})
        return data.get("comments", [])

    def save_pending_comment(self, comment_data: Dict[str, Any]) -> None:
        """
        Save a single pending comment to local JSON file.

        Args:
            comment_data: Comment data to save
        """
        pending_file = os.path.join(self.state_dir, "pending_comments.json")
        
        # Load existing data
        data = load_json_file(pending_file, {"version": "1.0", "comments": []})
        
        # Append new comment
        data["comments"].append(comment_data)
        
        # Save back
        save_json_file(pending_file, data, ensure_dir=False)

    def clear_pending_comments(self) -> None:
        """Clear all pending comments from local storage."""
        pending_file = os.path.join(self.state_dir, "pending_comments.json")
        save_json_file(
            pending_file,
            {"version": "1.0", "comments": []},
            ensure_dir=False
        )
