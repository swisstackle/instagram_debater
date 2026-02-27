"""
Local disk implementation of prompt storage.

Stores prompt templates in a JSON file on the local filesystem.
Default location: state/prompts.json
"""
from src.prompt_extractor import PromptExtractor
from src.base_json_extractor import BaseLocalDiskExtractor


class LocalDiskPromptExtractor(BaseLocalDiskExtractor, PromptExtractor):
    """
    Local disk implementation of prompt storage.

    Stores prompt templates in a JSON file on the local filesystem.
    Default location: state/prompts.json
    """

    def _get_filename(self) -> str:
        """Get the filename for prompt storage."""
        return "prompts.json"

    def get_prompt(self, name: str) -> str:
        """
        Get a prompt template by name from local disk.

        Args:
            name: The name/key of the prompt.

        Returns:
            The prompt template string, or empty string if not found.
        """
        data = self._load_data({"prompts": {}})
        return data.get("prompts", {}).get(name, "")

    def set_prompt(self, name: str, content: str) -> None:
        """
        Set a prompt template by name on local disk.

        Args:
            name: The name/key of the prompt.
            content: The prompt template content to store.
        """
        data = self._load_data({"prompts": {}})
        if "prompts" not in data:
            data["prompts"] = {}
        data["prompts"][name] = content
        self._save_data(data)

    def get_all_prompts(self) -> dict:
        """
        Get all stored prompt templates from local disk.

        Returns:
            Dictionary mapping prompt names to their content.
        """
        data = self._load_data({"prompts": {}})
        return data.get("prompts", {})
