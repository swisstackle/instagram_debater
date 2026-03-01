"""
Unit tests for AccountRegistry implementations.
"""
import os
import json
import tempfile
import pytest

from src.account_registry import AccountRegistry
from src.local_disk_account_registry import LocalDiskAccountRegistry
from src.account_registry_factory import create_account_registry


class TestLocalDiskAccountRegistry:
    """Tests for LocalDiskAccountRegistry."""

    @pytest.fixture
    def state_dir(self, tmp_path):
        """Provide a temporary state directory."""
        return str(tmp_path)

    @pytest.fixture
    def registry(self, state_dir):
        """Create a LocalDiskAccountRegistry with temp dir."""
        return LocalDiskAccountRegistry(state_dir=state_dir)

    def test_implements_interface(self, registry):
        """Registry implements the AccountRegistry abstract interface."""
        assert isinstance(registry, AccountRegistry)

    def test_get_accounts_empty_by_default(self, registry):
        """Registry returns empty list when no accounts stored."""
        accounts = registry.get_accounts()
        assert accounts == []

    def test_add_account(self, registry):
        """add_account stores a new account."""
        registry.add_account(account_id="123", username="testuser")
        accounts = registry.get_accounts()
        assert len(accounts) == 1
        assert accounts[0]["id"] == "123"
        assert accounts[0]["username"] == "testuser"

    def test_add_multiple_accounts(self, registry):
        """add_account supports multiple accounts."""
        registry.add_account(account_id="123", username="user_a")
        registry.add_account(account_id="456", username="user_b")
        accounts = registry.get_accounts()
        assert len(accounts) == 2
        ids = {a["id"] for a in accounts}
        assert ids == {"123", "456"}

    def test_add_account_updates_existing(self, registry):
        """add_account updates existing account when ID matches."""
        registry.add_account(account_id="123", username="old_name")
        registry.add_account(account_id="123", username="new_name")
        accounts = registry.get_accounts()
        assert len(accounts) == 1
        assert accounts[0]["username"] == "new_name"

    def test_get_account_by_id(self, registry):
        """get_account returns the correct account dict."""
        registry.add_account(account_id="123", username="testuser")
        registry.add_account(account_id="456", username="other")
        account = registry.get_account("123")
        assert account is not None
        assert account["id"] == "123"
        assert account["username"] == "testuser"

    def test_get_account_not_found_returns_none(self, registry):
        """get_account returns None for unknown ID."""
        result = registry.get_account("nonexistent")
        assert result is None

    def test_remove_account(self, registry):
        """remove_account deletes the account from the registry."""
        registry.add_account(account_id="123", username="testuser")
        result = registry.remove_account("123")
        assert result is True
        assert registry.get_accounts() == []

    def test_remove_nonexistent_account_returns_false(self, registry):
        """remove_account returns False when account not found."""
        result = registry.remove_account("nonexistent")
        assert result is False

    def test_remove_does_not_affect_other_accounts(self, registry):
        """remove_account only removes the targeted account."""
        registry.add_account(account_id="123", username="user_a")
        registry.add_account(account_id="456", username="user_b")
        registry.remove_account("123")
        remaining = registry.get_accounts()
        assert len(remaining) == 1
        assert remaining[0]["id"] == "456"

    def test_persists_to_file(self, state_dir, registry):
        """Accounts are persisted to disk."""
        registry.add_account(account_id="123", username="testuser")
        filepath = os.path.join(state_dir, "accounts.json")
        assert os.path.exists(filepath)
        with open(filepath) as f:
            data = json.load(f)
        assert len(data["accounts"]) == 1

    def test_loads_from_existing_file(self, state_dir):
        """Registry loads existing data from disk on init."""
        # Pre-populate file
        filepath = os.path.join(state_dir, "accounts.json")
        with open(filepath, "w") as f:
            json.dump({"accounts": [{"id": "abc", "username": "preloaded"}]}, f)
        new_registry = LocalDiskAccountRegistry(state_dir=state_dir)
        accounts = new_registry.get_accounts()
        assert len(accounts) == 1
        assert accounts[0]["id"] == "abc"

    def test_account_has_logged_in_at(self, registry):
        """add_account records a logged_in_at timestamp."""
        registry.add_account(account_id="123", username="testuser")
        account = registry.get_account("123")
        assert "logged_in_at" in account
        assert account["logged_in_at"]  # non-empty string


class TestAccountRegistryFactory:
    """Tests for create_account_registry factory function."""

    def test_creates_local_disk_registry_by_default(self, tmp_path):
        """Factory creates LocalDiskAccountRegistry by default."""
        registry = create_account_registry(state_dir=str(tmp_path))
        assert isinstance(registry, LocalDiskAccountRegistry)

    def test_registry_is_functional(self, tmp_path):
        """Factory-created registry can add and retrieve accounts."""
        registry = create_account_registry(state_dir=str(tmp_path))
        registry.add_account(account_id="999", username="factory_user")
        accounts = registry.get_accounts()
        assert len(accounts) == 1
        assert accounts[0]["id"] == "999"
