"""
Abstract interface for audit log storage backends.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AuditLogExtractor(ABC):
    """
    Abstract base class for audit log storage backends.
    
    Provides a consistent interface for saving, loading, and updating
    audit log entries regardless of the underlying storage mechanism
    (local disk, cloud storage, etc.).
    """

    @abstractmethod
    def save_entry(self, entry: Dict[str, Any]) -> None:
        """
        Save a new audit log entry.
        
        Args:
            entry: Audit log entry data (without ID - will be auto-generated)
        """

    @abstractmethod
    def load_entries(self) -> List[Dict[str, Any]]:
        """
        Load all audit log entries.
        
        Returns:
            List of audit log entries, empty list if none exist
        """

    @abstractmethod
    def update_entry(self, entry_id: str, updates: Dict[str, Any]) -> None:
        """
        Update an existing audit log entry.
        
        Args:
            entry_id: ID of the entry to update
            updates: Dictionary of fields to update
        """
