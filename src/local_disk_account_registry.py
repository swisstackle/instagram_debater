"""
Local disk implementation of account registry.

Stores the list of registered Instagram accounts in a JSON file on the filesystem.
Default location: state/accounts.json
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.account_registry import AccountRegistry
from src.base_json_extractor import BaseLocalDiskExtractor


class LocalDiskAccountRegistry(BaseLocalDiskExtractor, AccountRegistry):
    """
    Local disk implementation of account registry.

    Stores account metadata in a JSON file on the local filesystem.
    Default location: state/accounts.json
    """

    def _get_filename(self) -> str:
        """Get the filename for account registry storage."""
        return "accounts.json"

    def get_accounts(self) -> List[Dict]:
        """
        Get all registered accounts from local disk.

        Returns:
            List of account dicts.
        """
        data = self._load_data({"accounts": []})
        return data.get("accounts", [])

    def get_account(self, account_id: str) -> Optional[Dict]:
        """
        Get a single account by ID from local disk.

        Args:
            account_id: The unique identifier of the account.

        Returns:
            Account dict or None if not found.
        """
        for account in self.get_accounts():
            if account.get("id") == account_id:
                return account
        return None

    def add_account(self, account_id: str, username: str, **kwargs) -> None:
        """
        Add or update an account in the registry on local disk.

        Args:
            account_id: The unique identifier of the account.
            username: Instagram username.
            **kwargs: Additional metadata (e.g., logged_in_at).
        """
        data = self._load_data({"accounts": []})
        accounts = data.get("accounts", [])

        account = {
            "id": account_id,
            "username": username,
            "logged_in_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            **kwargs,
        }

        for i, existing in enumerate(accounts):
            if existing.get("id") == account_id:
                accounts[i] = account
                self._save_data({"accounts": accounts})
                return

        accounts.append(account)
        self._save_data({"accounts": accounts})

    def remove_account(self, account_id: str) -> bool:
        """
        Remove an account from the registry on local disk.

        Args:
            account_id: The unique identifier of the account.

        Returns:
            True if removed, False if not found.
        """
        data = self._load_data({"accounts": []})
        accounts = data.get("accounts", [])
        new_accounts = [a for a in accounts if a.get("id") != account_id]

        if len(new_accounts) == len(accounts):
            return False

        self._save_data({"accounts": new_accounts})
        return True
