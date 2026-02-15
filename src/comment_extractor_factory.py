"""
Factory for creating comment extractors based on configuration.
"""
import os

from src.comment_extractor import CommentExtractor
from src.local_disk_extractor import LocalDiskExtractor
from src.tigris_extractor import TigrisExtractor


def create_comment_extractor() -> CommentExtractor:
    """
    Create a comment extractor based on environment configuration.

    Returns:
        CommentExtractor instance (LocalDiskExtractor or TigrisExtractor)

    Environment variables:
        COMMENT_STORAGE_TYPE: Type of storage ('local' or 'tigris', default: 'local')
        
        For Tigris storage:
        - AWS_ACCESS_KEY_ID: Tigris access key ID
        - AWS_SECRET_ACCESS_KEY: Tigris secret access key
        - AWS_ENDPOINT_URL_S3: Tigris endpoint URL (default: https://fly.storage.tigris.dev)
        - TIGRIS_BUCKET_NAME: Tigris bucket name
        - AWS_REGION: AWS region (default: 'auto')
    """
    storage_type = os.getenv('COMMENT_STORAGE_TYPE', 'local').lower()

    if storage_type == 'tigris':
        return TigrisExtractor()
    else:
        # Default to local disk storage
        return LocalDiskExtractor()
