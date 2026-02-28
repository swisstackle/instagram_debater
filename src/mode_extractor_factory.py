"""
Factory function for creating mode extractors.
"""
import os
from typing import Optional

from src.mode_extractor import ModeExtractor
from src.local_disk_mode_extractor import LocalDiskModeExtractor
from src.tigris_mode_extractor import TigrisModeExtractor


def create_mode_extractor(state_dir: str = "state", account_id: Optional[str] = None) -> ModeExtractor:
    """
    Create a mode extractor based on environment configuration.

    Reads the MODE_STORAGE_TYPE environment variable to determine
    which implementation to use:
    - 'local' or unset: LocalDiskModeExtractor (default)
    - 'tigris': TigrisModeExtractor

    Args:
        state_dir: Directory for local disk storage (default: "state")
        account_id: Optional Instagram account ID for per-account namespacing.
            When provided, storage is scoped to state/accounts/{account_id}/.

    Returns:
        ModeExtractor: Configured mode extractor instance
    """
    storage_type = os.getenv('MODE_STORAGE_TYPE', 'local').lower()

    if storage_type == 'tigris':
        return TigrisModeExtractor(account_id=account_id)
    else:
        # Default to local disk storage
        if account_id:
            state_dir = os.path.join(state_dir, "accounts", account_id)
        return LocalDiskModeExtractor(state_dir=state_dir)
