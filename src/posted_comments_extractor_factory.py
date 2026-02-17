"""
Factory for creating posted comments extractor instances.
"""
import os
from src.posted_comments_extractor import PostedCommentsExtractor


def create_posted_comments_extractor() -> PostedCommentsExtractor:
    """
    Create a posted comments extractor based on environment configuration.
    
    Checks the POSTED_COMMENTS_STORAGE_TYPE environment variable to determine
    which implementation to use:
    - 'local' (default): Uses LocalDiskPostedExtractor
    - 'tigris': Uses TigrisPostedExtractor
    
    Returns:
        PostedCommentsExtractor instance
        
    Raises:
        ValueError: If POSTED_COMMENTS_STORAGE_TYPE is set to an invalid value
    """
    storage_type = os.environ.get('POSTED_COMMENTS_STORAGE_TYPE', 'local').lower()

    if storage_type == 'local':
        from src.local_disk_posted_extractor import LocalDiskPostedExtractor
        return LocalDiskPostedExtractor()
    elif storage_type == 'tigris':
        from src.tigris_posted_extractor import TigrisPostedExtractor
        return TigrisPostedExtractor()
    else:
        raise ValueError(
            f"Invalid POSTED_COMMENTS_STORAGE_TYPE: {storage_type}. "
            "Must be 'local' or 'tigris'."
        )
