"""
Unit tests for PromptExtractor implementations.

Tests follow TDD approach - tests written before implementation.
"""
import json
import os

import pytest

from tests.unit.test_extractor_base import BaseLocalDiskExtractorTests, BaseTigrisExtractorTests


class TestLocalDiskPromptExtractor(BaseLocalDiskExtractorTests):
    """Test suite for LocalDiskPromptExtractor."""

    @pytest.fixture
    def extractor(self, temp_state_dir):
        """Create a LocalDiskPromptExtractor instance."""
        from src.local_disk_prompt_extractor import LocalDiskPromptExtractor
        return LocalDiskPromptExtractor(state_dir=temp_state_dir)

    def test_implements_interface(self, extractor):
        """Test that LocalDiskPromptExtractor implements PromptExtractor interface."""
        from src.prompt_extractor import PromptExtractor
        assert isinstance(extractor, PromptExtractor)

    def test_get_prompt_returns_empty_when_not_set(self, extractor):
        """Test that get_prompt returns empty string when prompt not stored."""
        assert extractor.get_prompt("debate_prompt") == ""

    def test_set_then_get_prompt(self, extractor):
        """Test setting a prompt and reading it back."""
        content = "You are a debate assistant. Article: {{FULL_ARTICLE_TEXT}}"
        extractor.set_prompt("debate_prompt", content)
        assert extractor.get_prompt("debate_prompt") == content

    def test_set_multiple_prompts(self, extractor):
        """Test setting multiple prompts and reading them back independently."""
        extractor.set_prompt("debate_prompt", "Prompt A")
        extractor.set_prompt("relevance_prompt", "Prompt B")
        assert extractor.get_prompt("debate_prompt") == "Prompt A"
        assert extractor.get_prompt("relevance_prompt") == "Prompt B"

    def test_get_all_prompts_empty(self, extractor):
        """Test get_all_prompts returns empty dict when no prompts stored."""
        assert extractor.get_all_prompts() == {}

    def test_get_all_prompts_returns_all(self, extractor):
        """Test get_all_prompts returns all stored prompts."""
        extractor.set_prompt("prompt_a", "Content A")
        extractor.set_prompt("prompt_b", "Content B")
        all_prompts = extractor.get_all_prompts()
        assert all_prompts == {"prompt_a": "Content A", "prompt_b": "Content B"}

    def test_overwrite_existing_prompt(self, extractor):
        """Test that setting a prompt overwrites the previous value."""
        extractor.set_prompt("debate_prompt", "Old content")
        extractor.set_prompt("debate_prompt", "New content")
        assert extractor.get_prompt("debate_prompt") == "New content"

    def test_persists_to_file(self, extractor, temp_state_dir):
        """Test that prompts are persisted to disk."""
        extractor.set_prompt("debate_prompt", "My prompt content")
        prompts_file = os.path.join(temp_state_dir, "prompts.json")
        assert os.path.exists(prompts_file)
        with open(prompts_file, "r") as f:
            data = json.load(f)
        assert data["prompts"]["debate_prompt"] == "My prompt content"

    def test_loads_from_existing_file(self, temp_state_dir):
        """Test that prompts are loaded from an existing file."""
        from src.local_disk_prompt_extractor import LocalDiskPromptExtractor
        prompts_file = os.path.join(temp_state_dir, "prompts.json")
        with open(prompts_file, "w") as f:
            json.dump({"prompts": {"debate_prompt": "Stored prompt"}}, f)
        extractor = LocalDiskPromptExtractor(state_dir=temp_state_dir)
        assert extractor.get_prompt("debate_prompt") == "Stored prompt"

    def test_get_unknown_prompt_returns_empty(self, extractor):
        """Test that getting an unknown prompt name returns empty string."""
        extractor.set_prompt("known_prompt", "some content")
        assert extractor.get_prompt("unknown_prompt") == ""


class TestTigrisPromptExtractor(BaseTigrisExtractorTests):
    """Test suite for TigrisPromptExtractor using mocked S3."""

    @pytest.fixture
    def extractor(self, mock_s3_client, monkeypatch):
        """Create a TigrisPromptExtractor with mocked S3 client."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
        monkeypatch.setenv("TIGRIS_BUCKET_NAME", "test-bucket")
        from src.tigris_prompt_extractor import TigrisPromptExtractor
        ext = TigrisPromptExtractor()
        ext.s3_client = mock_s3_client
        return ext

    def test_implements_interface(self, extractor):
        """Test that TigrisPromptExtractor implements PromptExtractor interface."""
        from src.prompt_extractor import PromptExtractor
        assert isinstance(extractor, PromptExtractor)

    def test_get_prompt_returns_empty_when_no_key(self, extractor, mock_s3_client):
        """Test get_prompt returns empty string when S3 object doesn't exist."""
        self.setup_mock_no_such_key(mock_s3_client)
        assert extractor.get_prompt("debate_prompt") == ""

    def test_get_prompt_returns_value_from_s3(self, extractor, mock_s3_client):
        """Test get_prompt returns value when S3 object exists."""
        self.setup_mock_get_object(
            mock_s3_client,
            {"prompts": {"debate_prompt": "Stored prompt content"}}
        )
        assert extractor.get_prompt("debate_prompt") == "Stored prompt content"

    def test_get_prompt_returns_empty_for_missing_key(self, extractor, mock_s3_client):
        """Test get_prompt returns empty for a key not present in S3 data."""
        self.setup_mock_get_object(
            mock_s3_client,
            {"prompts": {"other_prompt": "Other content"}}
        )
        assert extractor.get_prompt("debate_prompt") == ""

    def test_set_prompt_saves_to_s3(self, extractor, mock_s3_client):
        """Test that set_prompt saves data to S3."""
        self.setup_mock_no_such_key(mock_s3_client)
        extractor.set_prompt("debate_prompt", "My prompt")
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        saved_data = json.loads(call_kwargs["Body"])
        assert saved_data["prompts"]["debate_prompt"] == "My prompt"

    def test_set_prompt_preserves_existing_prompts(self, extractor, mock_s3_client):
        """Test that set_prompt preserves other prompts when adding a new one."""
        self.setup_mock_get_object(
            mock_s3_client,
            {"prompts": {"existing_prompt": "Existing content"}}
        )
        extractor.set_prompt("new_prompt", "New content")
        call_kwargs = mock_s3_client.put_object.call_args[1]
        saved_data = json.loads(call_kwargs["Body"])
        assert saved_data["prompts"]["existing_prompt"] == "Existing content"
        assert saved_data["prompts"]["new_prompt"] == "New content"

    def test_get_all_prompts_returns_empty_when_no_key(self, extractor, mock_s3_client):
        """Test get_all_prompts returns empty dict when S3 object doesn't exist."""
        self.setup_mock_no_such_key(mock_s3_client)
        assert extractor.get_all_prompts() == {}

    def test_get_all_prompts_returns_all_from_s3(self, extractor, mock_s3_client):
        """Test get_all_prompts returns all prompts stored in S3."""
        self.setup_mock_get_object(
            mock_s3_client,
            {"prompts": {"p1": "Content 1", "p2": "Content 2"}}
        )
        result = extractor.get_all_prompts()
        assert result == {"p1": "Content 1", "p2": "Content 2"}

    def test_object_key_is_correct(self, extractor):
        """Test that the S3 object key is correct."""
        assert extractor._get_object_key() == "state/prompts.json"


class TestPromptExtractorFactory:
    """Test suite for prompt extractor factory function."""

    def test_factory_returns_local_by_default(self, monkeypatch, tmp_path):
        """Test factory returns LocalDiskPromptExtractor when PROMPT_STORAGE_TYPE not set."""
        monkeypatch.delenv("PROMPT_STORAGE_TYPE", raising=False)
        from src.prompt_extractor_factory import create_prompt_extractor
        from src.local_disk_prompt_extractor import LocalDiskPromptExtractor
        extractor = create_prompt_extractor(state_dir=str(tmp_path))
        assert isinstance(extractor, LocalDiskPromptExtractor)

    def test_factory_returns_local_explicitly(self, monkeypatch, tmp_path):
        """Test factory returns LocalDiskPromptExtractor when PROMPT_STORAGE_TYPE=local."""
        monkeypatch.setenv("PROMPT_STORAGE_TYPE", "local")
        from src.prompt_extractor_factory import create_prompt_extractor
        from src.local_disk_prompt_extractor import LocalDiskPromptExtractor
        extractor = create_prompt_extractor(state_dir=str(tmp_path))
        assert isinstance(extractor, LocalDiskPromptExtractor)

    def test_factory_uses_custom_state_dir(self, monkeypatch, tmp_path):
        """Test factory passes state_dir to LocalDiskPromptExtractor."""
        monkeypatch.delenv("PROMPT_STORAGE_TYPE", raising=False)
        from src.prompt_extractor_factory import create_prompt_extractor
        extractor = create_prompt_extractor(state_dir=str(tmp_path))
        assert extractor.state_dir == str(tmp_path)

    def test_factory_returns_tigris(self, monkeypatch):
        """Test factory returns TigrisPromptExtractor when PROMPT_STORAGE_TYPE=tigris."""
        monkeypatch.setenv("PROMPT_STORAGE_TYPE", "tigris")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
        monkeypatch.setenv("TIGRIS_BUCKET_NAME", "test-bucket")
        from src.prompt_extractor_factory import create_prompt_extractor
        from src.tigris_prompt_extractor import TigrisPromptExtractor
        extractor = create_prompt_extractor()
        assert isinstance(extractor, TigrisPromptExtractor)
