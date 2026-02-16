"""
Local disk implementation of audit log storage.
"""
import os
from typing import Any, Dict, List

from src.audit_log_extractor import AuditLogExtractor
from src.file_utils import load_json_file, save_json_file


class LocalDiskAuditExtractor(AuditLogExtractor):
    """
    Local disk implementation of audit log storage.
    
    Stores audit log entries in a JSON file on the local filesystem.
    Default location: state/audit_log.json
    """

    def __init__(self, state_dir: str = "state"):
        """
        Initialize local disk audit log extractor.
        
        Args:
            state_dir: Directory for storing state files (default: "state")
        """
        self.state_dir = state_dir
        self.audit_file = os.path.join(state_dir, "audit_log.json")

    def save_entry(self, entry: Dict[str, Any]) -> None:
        """
        Save a new audit log entry to local disk.
        
        Args:
            entry: Audit log entry data (without ID - will be auto-generated)
        """
        # Ensure state directory exists
        os.makedirs(self.state_dir, exist_ok=True)

        # Load existing entries
        data = load_json_file(self.audit_file)
        if data is None:
            data = {"version": "1.0", "entries": []}

        # Auto-generate entry ID
        entry_copy = entry.copy()
        entry_copy["id"] = f"log_{len(data['entries']) + 1:03d}"

        # Append entry
        data["entries"].append(entry_copy)

        # Save
        save_json_file(self.audit_file, data)

    def load_entries(self) -> List[Dict[str, Any]]:
        """
        Load all audit log entries from local disk.
        
        Returns:
            List of audit log entries, empty list if file doesn't exist
        """
        data = load_json_file(self.audit_file)
        if data is None:
            return []
        return data.get("entries", [])

    def update_entry(self, entry_id: str, updates: Dict[str, Any]) -> None:
        """
        Update an existing audit log entry on local disk.
        
        Args:
            entry_id: ID of the entry to update
            updates: Dictionary of fields to update
        """
        data = load_json_file(self.audit_file)
        if data is None:
            return

        # Find and update entry
        for entry in data.get("entries", []):
            if entry.get("id") == entry_id:
                entry.update(updates)
                break

        # Save updated data
        save_json_file(self.audit_file, data)
