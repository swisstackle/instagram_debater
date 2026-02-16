"""
Local disk implementation of audit log storage.
"""
from typing import Any, Dict, List

from src.audit_log_extractor import AuditLogExtractor
from src.base_json_extractor import BaseLocalDiskExtractor


class LocalDiskAuditExtractor(BaseLocalDiskExtractor, AuditLogExtractor):
    """
    Local disk implementation of audit log storage.
    
    Stores audit log entries in a JSON file on the local filesystem.
    Default location: state/audit_log.json
    """

    def _get_filename(self) -> str:
        """Get the filename for audit log storage."""
        return "audit_log.json"

    def save_entry(self, entry: Dict[str, Any]) -> None:
        """
        Save a new audit log entry to local disk.
        
        Args:
            entry: Audit log entry data (without ID - will be auto-generated)
        """
        # Load existing entries
        data = self._load_data({"version": "1.0", "entries": []})

        # Auto-generate entry ID
        entry_copy = entry.copy()
        entry_copy["id"] = f"log_{len(data['entries']) + 1:03d}"

        # Append entry
        data["entries"].append(entry_copy)

        # Save
        self._save_data(data)

    def load_entries(self) -> List[Dict[str, Any]]:
        """
        Load all audit log entries from local disk.
        
        Returns:
            List of audit log entries, empty list if file doesn't exist
        """
        data = self._load_data({"version": "1.0", "entries": []})
        return data.get("entries", [])

    def update_entry(self, entry_id: str, updates: Dict[str, Any]) -> None:
        """
        Update an existing audit log entry on local disk.
        
        Args:
            entry_id: ID of the entry to update
            updates: Dictionary of fields to update
        """
        data = self._load_data({"version": "1.0", "entries": []})
        
        # If no entries, nothing to update
        if not data.get("entries"):
            return

        # Find and update entry
        for entry in data.get("entries", []):
            if entry.get("id") == entry_id:
                entry.update(updates)
                break

        # Save updated data
        self._save_data(data)
