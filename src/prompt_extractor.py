"""
Abstract interface for prompt storage backends.

Defines the interface for getting and setting prompt templates.
Implementations can store prompts locally or in distributed storage (Tigris/S3),
allowing all components (dashboard, processor) to share the same prompt templates.
"""
from abc import ABC, abstractmethod


class PromptExtractor(ABC):
    """Abstract base class for prompt storage backends."""

    @abstractmethod
    def get_prompt(self, name: str) -> str:
        """
        Get a prompt template by name.

        Args:
            name: The name/key of the prompt (e.g., "debate_prompt").

        Returns:
            The prompt template string, or empty string if not found.
        """

    @abstractmethod
    def set_prompt(self, name: str, content: str) -> None:
        """
        Set a prompt template by name.

        Args:
            name: The name/key of the prompt (e.g., "debate_prompt").
            content: The prompt template content to store.
        """

    @abstractmethod
    def get_all_prompts(self) -> dict:
        """
        Get all stored prompt templates.

        Returns:
            Dictionary mapping prompt names to their content.
        """
