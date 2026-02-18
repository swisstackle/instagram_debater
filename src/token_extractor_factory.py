"""
Factory function for creating token extractors.

Selects the appropriate token storage backend based on environment variable.
"""
import os

from src.token_extractor import TokenExtractor
from src.local_disk_token_extractor import LocalDiskTokenExtractor
from src.tigris_token_extractor import TigrisTokenExtractor


def create_token_extractor(state_dir: str = "state") -> TokenExtractor:
    """
    Create a token extractor instance based on configuration.

    Args:
        state_dir: Directory for local storage (only used for local implementation)

    Returns:
        TokenExtractor instance (LocalDiskTokenExtractor or TigrisTokenExtractor)

    Environment Variables:
        OAUTH_TOKEN_STORAGE_TYPE: Storage backend ('local' or 'tigris', default: 'local')
        AWS_ACCESS_KEY_ID: Required for Tigris storage
        AWS_SECRET_ACCESS_KEY: Required for Tigris storage
        TIGRIS_BUCKET_NAME: Required for Tigris storage
    """
    storage_type = os.getenv("OAUTH_TOKEN_STORAGE_TYPE", "local").lower()

    if storage_type == "tigris":
        return TigrisTokenExtractor()
    elif storage_type == "local":
        return LocalDiskTokenExtractor(state_dir=state_dir)

    # Default to local for any other value (including "local", "", None, etc.)
    return LocalDiskTokenExtractor(state_dir=state_dir)
