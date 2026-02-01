"""
File utility functions for Instagram Debate Bot.
Common file operations to avoid code duplication.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict


def load_json_file(filepath: str, default: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load a JSON file with a default fallback.

    Args:
        filepath: Path to the JSON file
        default: Default value if file doesn't exist

    Returns:
        Loaded JSON data or default value
    """
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default


def save_json_file(filepath: str, data: Dict[str, Any], ensure_dir: bool = True) -> None:
    """
    Save data to a JSON file.

    Args:
        filepath: Path to save the JSON file
        data: Data to save
        ensure_dir: Whether to create parent directory if it doesn't exist
    """
    if ensure_dir:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def get_utc_timestamp() -> str:
    """
    Get current UTC timestamp in ISO format.

    Returns:
        ISO formatted timestamp string without +00:00 suffix
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
