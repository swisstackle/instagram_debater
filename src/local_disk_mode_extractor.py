"""
Local disk implementation of mode storage.

Stores the auto-post mode setting in a JSON file on the local filesystem.
Default location: state/mode.json
"""
from src.mode_extractor import ModeExtractor
from src.base_json_extractor import BaseLocalDiskExtractor


class LocalDiskModeExtractor(BaseLocalDiskExtractor, ModeExtractor):
    """
    Local disk implementation of mode storage.

    Stores the auto-post mode in a JSON file on the local filesystem.
    Default location: state/mode.json
    """

    def _get_filename(self) -> str:
        """Get the filename for mode storage."""
        return "mode.json"

    def get_auto_mode(self) -> bool:
        """
        Get the current auto-post mode from local disk.

        Returns:
            True if auto-posting is enabled, False otherwise (default: False).
        """
        data = self._load_data({"auto_mode": False})
        return bool(data.get("auto_mode", False))

    def set_auto_mode(self, value: bool) -> None:
        """
        Set the auto-post mode on local disk.

        Args:
            value: True to enable auto-posting, False to disable.
        """
        self._save_data({"auto_mode": value})
