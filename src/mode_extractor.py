"""
Abstract interface for mode storage backends.

Defines the interface for getting and setting the auto-post mode.
Implementations can store the mode locally or in distributed storage (Tigris/S3),
allowing all components (dashboard, processor, webhook) to share the same setting.
"""
from abc import ABC, abstractmethod


class ModeExtractor(ABC):
    """Abstract base class for mode storage backends."""

    @abstractmethod
    def get_auto_mode(self) -> bool:
        """
        Get the current auto-post mode.

        Returns:
            True if auto-posting is enabled, False otherwise.
        """

    @abstractmethod
    def set_auto_mode(self, value: bool) -> None:
        """
        Set the auto-post mode.

        Args:
            value: True to enable auto-posting, False to disable.
        """
