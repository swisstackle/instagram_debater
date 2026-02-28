"""
Tigris/S3-compatible storage implementation of prompt storage.

Stores prompt templates in an S3-compatible object storage service,
allowing all distributed components (dashboard, processor) to share
the same prompt templates.
Default object key: state/prompts.json
"""
from typing import Optional

from src.prompt_extractor import PromptExtractor
from src.base_json_extractor import BaseTigrisExtractor


class TigrisPromptExtractor(BaseTigrisExtractor, PromptExtractor):
    """
    Tigris/S3-compatible storage implementation of prompt storage.

    Stores prompt templates in an S3-compatible object storage service.
    Default object key: state/prompts.json
    """

    def __init__(self, account_id: Optional[str] = None, **kwargs):
        """
        Initialize the Tigris prompt extractor.

        Args:
            account_id: Optional Instagram account ID for per-account namespacing.
            **kwargs: Additional keyword arguments passed to BaseTigrisExtractor.
        """
        super().__init__(**kwargs)
        self.account_id = account_id

    def _get_object_key(self) -> str:
        """Get the S3 object key for prompt storage."""
        if self.account_id:
            return f"state/accounts/{self.account_id}/prompts.json"
        return "state/prompts.json"

    def get_prompt(self, name: str) -> str:
        """
        Get a prompt template by name from S3.

        Args:
            name: The name/key of the prompt.

        Returns:
            The prompt template string, or empty string if not found.
        """
        data = self._load_from_s3()
        if data is None:
            return ""
        return data.get("prompts", {}).get(name, "")

    def set_prompt(self, name: str, content: str) -> None:
        """
        Set a prompt template by name in S3.

        Args:
            name: The name/key of the prompt.
            content: The prompt template content to store.
        """
        data = self._load_from_s3()
        if data is None:
            data = {"prompts": {}}
        if "prompts" not in data:
            data["prompts"] = {}
        data["prompts"][name] = content
        self._save_to_s3(data)

    def get_all_prompts(self) -> dict:
        """
        Get all stored prompt templates from S3.

        Returns:
            Dictionary mapping prompt names to their content.
        """
        data = self._load_from_s3()
        if data is None:
            return {}
        return data.get("prompts", {})
