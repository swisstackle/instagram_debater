"""
Abstract interface for account registry.

Defines the interface for storing and retrieving registered Instagram accounts.
Implementations can store the registry locally or in distributed storage (Tigris/S3).
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class AccountRegistry(ABC):
    """Abstract base class for account registry backends."""

    @abstractmethod
    def get_accounts(self) -> List[Dict]:
        """
        Get all registered accounts.

        Returns:
            List of account dicts with at least 'id' and 'username' keys.
        """

    @abstractmethod
    def get_account(self, account_id: str) -> Optional[Dict]:
        """
        Get a single account by ID.

        Args:
            account_id: The unique identifier of the account (Instagram user_id).

        Returns:
            Account dict or None if not found.
        """

    @abstractmethod
    def add_account(self, account_id: str, username: str, **kwargs) -> None:
        """
        Add or update an account in the registry.

        Args:
            account_id: The unique identifier of the account (Instagram user_id).
            username: Instagram username.
            **kwargs: Additional metadata (e.g., logged_in_at).
        """

    @abstractmethod
    def remove_account(self, account_id: str) -> bool:
        """
        Remove an account from the registry.

        Args:
            account_id: The unique identifier of the account.

        Returns:
            True if the account was removed, False if it was not found.
        """
