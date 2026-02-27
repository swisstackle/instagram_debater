"""
Factory function for creating prompt extractors.
"""
import os

from src.prompt_extractor import PromptExtractor
from src.local_disk_prompt_extractor import LocalDiskPromptExtractor
from src.tigris_prompt_extractor import TigrisPromptExtractor


def create_prompt_extractor(state_dir: str = "state") -> PromptExtractor:
    """
    Create a prompt extractor based on environment configuration.

    Reads the PROMPT_STORAGE_TYPE environment variable to determine
    which implementation to use:
    - 'local' or unset: LocalDiskPromptExtractor (default)
    - 'tigris': TigrisPromptExtractor

    Args:
        state_dir: Directory for local disk storage (default: "state")

    Returns:
        PromptExtractor: Configured prompt extractor instance
    """
    storage_type = os.getenv('PROMPT_STORAGE_TYPE', 'local').lower()

    if storage_type == 'tigris':
        return TigrisPromptExtractor()
    else:
        # Default to local disk storage
        return LocalDiskPromptExtractor(state_dir=state_dir)
