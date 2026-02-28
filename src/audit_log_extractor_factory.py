"""
Factory function for creating audit log extractors.
"""
import os
from typing import Optional

from src.audit_log_extractor import AuditLogExtractor
from src.local_disk_audit_extractor import LocalDiskAuditExtractor
from src.tigris_audit_extractor import TigrisAuditExtractor


def create_audit_log_extractor(state_dir: str = "state", account_id: Optional[str] = None) -> AuditLogExtractor:
    """
    Create an audit log extractor based on environment configuration.
    
    Reads the AUDIT_LOG_STORAGE_TYPE environment variable to determine
    which implementation to use:
    - 'local' or unset: LocalDiskAuditExtractor (default)
    - 'tigris': TigrisAuditExtractor
    
    Args:
        state_dir: Directory for local disk storage (default: "state").
            Only used when AUDIT_LOG_STORAGE_TYPE is 'local' or unset.
        account_id: Optional Instagram account ID for per-account namespacing.
            When provided, storage is scoped to state/accounts/{account_id}/.
    
    Returns:
        AuditLogExtractor: Configured audit log extractor instance
    """
    storage_type = os.getenv('AUDIT_LOG_STORAGE_TYPE', 'local').lower()

    if storage_type == 'tigris':
        return TigrisAuditExtractor(account_id=account_id)
    else:
        # Default to local disk storage
        if account_id:
            state_dir = os.path.join(state_dir, "accounts", account_id)
        return LocalDiskAuditExtractor(state_dir=state_dir)
