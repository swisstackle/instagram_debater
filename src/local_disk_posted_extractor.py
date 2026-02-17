"""
Local disk implementation of posted comments storage.
"""
import os
from typing import Set

from src.posted_comments_extractor import PostedCommentsExtractor


class LocalDiskPostedExtractor(PostedCommentsExtractor):
    """
    Local disk implementation of posted comments storage.
    
    Stores posted comment IDs in a simple text file on the local filesystem.
    Default location: state/posted_ids.txt
    """

    def __init__(self, state_dir: str = "state"):
        """
        Initialize local disk posted comments extractor.
        
        Args:
            state_dir: Directory for storing state files (default: "state")
        """
        self.state_dir = state_dir
        self._filename = "posted_ids.txt"

    def _get_filepath(self) -> str:
        """Get the full file path for storage."""
        return os.path.join(self.state_dir, self._filename)

    def load_posted_ids(self) -> Set[str]:
        """
        Load all posted comment IDs from local disk.
        
        Returns:
            Set of comment IDs that have been posted
        """
        filepath = self._get_filepath()
        if not os.path.exists(filepath):
            return set()

        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Strip whitespace and filter out empty lines
        return {line.strip() for line in lines if line.strip()}

    def is_posted(self, comment_id: str) -> bool:
        """
        Check if a comment ID has already been posted.
        
        Args:
            comment_id: The Instagram comment ID to check
            
        Returns:
            True if the comment has been posted, False otherwise
        """
        posted_ids = self.load_posted_ids()
        return comment_id in posted_ids

    def add_posted_id(self, comment_id: str) -> None:
        """
        Add a comment ID to the posted list.
        
        Args:
            comment_id: The Instagram comment ID to mark as posted
        """
        # Check if already posted to avoid duplicates
        if self.is_posted(comment_id):
            return

        # Create state directory if it doesn't exist
        os.makedirs(self.state_dir, exist_ok=True)

        # Append comment ID to file
        filepath = self._get_filepath()
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(f"{comment_id}\n")
