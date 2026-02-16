"""
Tigris/S3-compatible storage implementation of audit log storage.
"""
from typing import Any, Dict, List

from src.audit_log_extractor import AuditLogExtractor
from src.base_json_extractor import BaseTigrisExtractor


class TigrisAuditExtractor(BaseTigrisExtractor, AuditLogExtractor):
    """
    Tigris/S3-compatible storage implementation of audit log storage.
    
    Stores audit log entries in an S3-compatible object storage service.
    Default object key: state/audit_log.json
    """

    def _get_object_key(self) -> str:
        """Get the S3 object key for audit log storage."""
        return "state/audit_log.json"

    def save_entry(self, entry: Dict[str, Any]) -> None:
        """
        Save a new audit log entry to S3.
        
        Args:
            entry: Audit log entry data (without ID - will be auto-generated)
        """
        # Load existing entries
        data = self._load_from_s3()
        if data is None:
            data = {"version": "1.0", "entries": []}

        # Auto-generate entry ID
        entry_copy = entry.copy()
        entry_copy["id"] = f"log_{len(data['entries']) + 1:03d}"

        # Append entry
        data["entries"].append(entry_copy)

        # Save to S3
        self._save_to_s3(data)

    def load_entries(self) -> List[Dict[str, Any]]:
        """
        Load all audit log entries from S3.
        
        Returns:
            List of audit log entries, empty list if object doesn't exist
        """
        data = self._load_from_s3()
        if data is None:
            return []
        return data.get("entries", [])

    def update_entry(self, entry_id: str, updates: Dict[str, Any]) -> None:
        """
        Update an existing audit log entry in S3.
        
        Args:
            entry_id: ID of the entry to update
            updates: Dictionary of fields to update
        """
        data = self._load_from_s3()
        if data is None:
            return

        # Find and update entry
        for entry in data.get("entries", []):
            if entry.get("id") == entry_id:
                entry.update(updates)
                break

        # Save updated data
        self._save_to_s3(data)
