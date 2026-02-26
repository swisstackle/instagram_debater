"""
Tigris/S3-compatible storage implementation of mode storage.

Stores the auto-post mode setting in an S3-compatible object storage service,
allowing all distributed components (dashboard, processor, webhook) to share
the same mode setting.
Default object key: state/mode.json
"""
from src.mode_extractor import ModeExtractor
from src.base_json_extractor import BaseTigrisExtractor


class TigrisModeExtractor(BaseTigrisExtractor, ModeExtractor):
    """
    Tigris/S3-compatible storage implementation of mode storage.

    Stores the auto-post mode in an S3-compatible object storage service.
    Default object key: state/mode.json
    """

    def _get_object_key(self) -> str:
        """Get the S3 object key for mode storage."""
        return "state/mode.json"

    def get_auto_mode(self) -> bool:
        """
        Get the current auto-post mode from S3.

        Returns:
            True if auto-posting is enabled, False otherwise (default: False).
        """
        data = self._load_from_s3()
        if data is None:
            return False
        return bool(data.get("auto_mode", False))

    def set_auto_mode(self, value: bool) -> None:
        """
        Set the auto-post mode in S3.

        Args:
            value: True to enable auto-posting, False to disable.
        """
        self._save_to_s3({"auto_mode": value})
