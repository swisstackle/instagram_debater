"""
Factory function for creating account registries.

Selects the appropriate storage backend based on environment variable.
"""
import os

from src.account_registry import AccountRegistry
from src.local_disk_account_registry import LocalDiskAccountRegistry


def create_account_registry(state_dir: str = "state") -> AccountRegistry:
    """
    Create an account registry based on environment configuration.

    Reads the ACCOUNT_REGISTRY_STORAGE_TYPE environment variable to determine
    which implementation to use:
    - 'local' or unset: LocalDiskAccountRegistry (default)

    Args:
        state_dir: Directory for local disk storage (default: "state")

    Returns:
        AccountRegistry: Configured account registry instance
    """
    # Only local disk is currently supported; Tigris support can be added later
    return LocalDiskAccountRegistry(state_dir=state_dir)
