"""
Factory function for creating token extractors.

Selects the appropriate token storage backend based on environment variable.
"""
import os
from typing import Optional

from src.token_extractor import TokenExtractor
from src.local_disk_token_extractor import LocalDiskTokenExtractor
from src.tigris_token_extractor import TigrisTokenExtractor
from src.env_var_token_extractor import EnvVarTokenExtractor


def create_token_extractor(state_dir: str = "state", account_id: Optional[str] = None) -> TokenExtractor:
    """
    Create a token extractor instance based on configuration.

    Args:
        state_dir: Directory for local storage (only used for local implementation)
        account_id: Optional Instagram account ID for per-account namespacing.
            When provided, storage is scoped to state/accounts/{account_id}/.

    Returns:
        TokenExtractor instance (LocalDiskTokenExtractor, TigrisTokenExtractor, or EnvVarTokenExtractor)

    Environment Variables:
        OAUTH_TOKEN_STORAGE_TYPE: Storage backend ('local', 'tigris', or 'env_var', default: 'local')
        AWS_ACCESS_KEY_ID: Required for Tigris storage
        AWS_SECRET_ACCESS_KEY: Required for Tigris storage
        TIGRIS_BUCKET_NAME: Required for Tigris storage
        INSTAGRAM_ACCESS_TOKEN: Required for env_var storage
    """
    storage_type = os.getenv("OAUTH_TOKEN_STORAGE_TYPE", "local").lower()

    if storage_type == "tigris":
        return TigrisTokenExtractor(account_id=account_id)
    elif storage_type == "env_var":
        return EnvVarTokenExtractor()

    # Default to local for any other value (including "local", "", None, etc.)
    if account_id:
        state_dir = os.path.join(state_dir, "accounts", account_id)
    return LocalDiskTokenExtractor(state_dir=state_dir)
