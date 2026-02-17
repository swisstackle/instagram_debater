"""
Abstract interface for posted comments storage backends.
"""
from abc import ABC, abstractmethod
from typing import Set


class PostedCommentsExtractor(ABC):
    """
    Abstract base class for posted comments storage backends.
    
    Provides a consistent interface for tracking which comment IDs have already
    been responded to, regardless of the underlying storage mechanism
    (local disk, cloud storage, etc.).
    """

    @abstractmethod
    def add_posted_id(self, comment_id: str) -> None:
        """
        Add a comment ID to the posted list.
        
        Args:
            comment_id: The Instagram comment ID to mark as posted
        """

    @abstractmethod
    def is_posted(self, comment_id: str) -> bool:
        """
        Check if a comment ID has already been posted.
        
        Args:
            comment_id: The Instagram comment ID to check
            
        Returns:
            True if the comment has been posted, False otherwise
        """

    @abstractmethod
    def load_posted_ids(self) -> Set[str]:
        """
        Load all posted comment IDs.
        
        Returns:
            Set of comment IDs that have been posted
        """
