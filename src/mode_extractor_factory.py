"""
Factory function for creating mode extractors.
"""
import os

from src.mode_extractor import ModeExtractor
from src.local_disk_mode_extractor import LocalDiskModeExtractor
from src.tigris_mode_extractor import TigrisModeExtractor


def create_mode_extractor() -> ModeExtractor:
    """
    Create a mode extractor based on environment configuration.

    Reads the MODE_STORAGE_TYPE environment variable to determine
    which implementation to use:
    - 'local' or unset: LocalDiskModeExtractor (default)
    - 'tigris': TigrisModeExtractor

    Returns:
        ModeExtractor: Configured mode extractor instance
    """
    storage_type = os.getenv('MODE_STORAGE_TYPE', 'local').lower()

    if storage_type == 'tigris':
        return TigrisModeExtractor()
    else:
        # Default to local disk storage
        return LocalDiskModeExtractor()
