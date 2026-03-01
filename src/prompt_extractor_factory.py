"""
Factory function for creating prompt extractors.
"""
import os
from typing import Optional

from src.prompt_extractor import PromptExtractor
from src.local_disk_prompt_extractor import LocalDiskPromptExtractor
from src.tigris_prompt_extractor import TigrisPromptExtractor


def create_prompt_extractor(state_dir: str = "state", account_id: Optional[str] = None) -> PromptExtractor:
    """
    Create a prompt extractor based on environment configuration.

    Reads the PROMPT_STORAGE_TYPE environment variable to determine
    which implementation to use:
    - 'local' or unset: LocalDiskPromptExtractor (default)
    - 'tigris': TigrisPromptExtractor

    Args:
        state_dir: Directory for local disk storage (default: "state")
        account_id: Optional Instagram account ID for per-account namespacing.
            When provided, storage is scoped to state/accounts/{account_id}/.

    Returns:
        PromptExtractor: Configured prompt extractor instance
    """
    storage_type = os.getenv('PROMPT_STORAGE_TYPE', 'local').lower()

    if storage_type == 'tigris':
        print("Using TigrisPromptExtractor for runtime-editable templates.")
        return TigrisPromptExtractor(account_id=account_id)
    else:
        # Default to local disk storage
        if account_id:
            state_dir = os.path.join(state_dir, "accounts", account_id)
        print("Using LocalDiskPromptExtractor for static templates.")
        return LocalDiskPromptExtractor(state_dir=state_dir)
