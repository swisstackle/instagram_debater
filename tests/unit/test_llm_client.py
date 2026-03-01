"""
Unit tests for LLMClient integration with PromptExtractor.

Tests follow TDD approach - tests written before implementation.
"""
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch, mock_open

import pytest


class TestLLMClientPromptExtractorIntegration:
    """Test suite for LLMClient integration with PromptExtractor."""

    @pytest.fixture
    def temp_state_dir(self):
        """Create a temporary state directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def prompt_extractor(self, temp_state_dir):
        """Create a LocalDiskPromptExtractor with temporary state directory."""
        from src.local_disk_prompt_extractor import LocalDiskPromptExtractor
        return LocalDiskPromptExtractor(state_dir=temp_state_dir)

    @pytest.fixture
    def llm_client_with_extractor(self, prompt_extractor):
        """Create an LLMClient with a LocalDiskPromptExtractor."""
        from src.llm_client import LLMClient
        return LLMClient(
            api_key="test_key",
            model_name="test-model",
            prompt_extractor=prompt_extractor
        )

    # ================== CONSTRUCTOR TESTS ==================

    def test_llm_client_accepts_prompt_extractor(self, prompt_extractor):
        """Test that LLMClient can be constructed with a prompt_extractor argument."""
        from src.llm_client import LLMClient
        client = LLMClient(
            api_key="test_key",
            model_name="test-model",
            prompt_extractor=prompt_extractor
        )
        assert client.prompt_extractor is prompt_extractor

    def test_llm_client_defaults_to_factory_prompt_extractor(self):
        """Test that LLMClient creates a prompt_extractor via factory when none provided."""
        from src.llm_client import LLMClient
        from src.prompt_extractor import PromptExtractor
        client = LLMClient(api_key="test_key", model_name="test-model")
        assert isinstance(client.prompt_extractor, PromptExtractor)

    # ================== LOAD TEMPLATE OVERRIDE TESTS ==================

    def test_load_template_returns_stored_prompt_when_available(
        self, llm_client_with_extractor, prompt_extractor
    ):
        """Test that load_template returns stored prompt when extractor has it."""
        prompt_extractor.set_prompt("debate_prompt", "Stored debate prompt content")
        result = llm_client_with_extractor.load_template("debate_prompt.txt")
        assert result == "Stored debate prompt content"

    def test_load_template_falls_back_to_file_when_no_stored_prompt(self, temp_state_dir):
        """Test that load_template falls back to filesystem when no stored prompt."""
        from src.llm_client import LLMClient
        mock_extractor = MagicMock()
        mock_extractor.get_prompt.return_value = ""
        client = LLMClient(api_key="test_key", model_name="test-model",
                           prompt_extractor=mock_extractor)
        file_content = "File-based template content"
        with patch("builtins.open", mock_open(read_data=file_content)):
            result = client.load_template("debate_prompt.txt")
        assert result == file_content

    def test_load_template_falls_back_to_file_when_stored_prompt_is_empty(self, temp_state_dir):
        """Test that load_template falls back to file when stored prompt is empty string."""
        from src.llm_client import LLMClient
        mock_extractor = MagicMock()
        mock_extractor.get_prompt.return_value = ""
        client = LLMClient(api_key="test_key", model_name="test-model",
                           prompt_extractor=mock_extractor)
        file_content = "File-based template content"
        with patch("builtins.open", mock_open(read_data=file_content)):
            result = client.load_template("debate_prompt.txt")
        assert result == file_content

    def test_load_template_stored_prompt_overrides_file(self, temp_state_dir):
        """Test that stored prompt completely overrides file-based template."""
        from src.llm_client import LLMClient
        stored_content = "Custom stored prompt"
        mock_extractor = MagicMock()
        mock_extractor.get_prompt.return_value = stored_content
        client = LLMClient(api_key="test_key", model_name="test-model",
                           prompt_extractor=mock_extractor)
        result = client.load_template("post_topic_check_prompt.txt")
        assert result == stored_content

    def test_load_template_strips_txt_extension_for_lookup(
        self, llm_client_with_extractor, prompt_extractor
    ):
        """Test that .txt extension is stripped when looking up stored prompts."""
        prompt_extractor.set_prompt("comment_relevance_check_prompt", "Custom relevance check")
        result = llm_client_with_extractor.load_template(
            "comment_relevance_check_prompt.txt"
        )
        assert result == "Custom relevance check"

    def test_load_template_handles_template_without_txt_extension(
        self, llm_client_with_extractor, prompt_extractor
    ):
        """Test that load_template works when template name has no .txt extension."""
        prompt_extractor.set_prompt("debate_prompt", "Stored content")
        result = llm_client_with_extractor.load_template("debate_prompt")
        assert result == "Stored content"

    def test_load_template_falls_back_for_unnumbered_variant(
        self, llm_client_with_extractor, prompt_extractor
    ):
        """Test that unnumbered debate_prompt variant also works with extractor."""
        prompt_extractor.set_prompt("debate_prompt_unnumbered", "Unnumbered version")
        result = llm_client_with_extractor.load_template("debate_prompt_unnumbered.txt")
        assert result == "Unnumbered version"

    def test_load_template_no_filesystem_read_when_prompt_stored(self, temp_state_dir):
        """Test that filesystem templates are not read when a stored prompt is available."""
        from src.llm_client import LLMClient
        mock_extractor = MagicMock()
        mock_extractor.get_prompt.return_value = "Stored content"
        client = LLMClient(api_key="test_key", model_name="test-model",
                           prompt_extractor=mock_extractor)
        result = client.load_template("debate_prompt.txt")
        assert result == "Stored content"
        # Extractor was consulted
        mock_extractor.get_prompt.assert_called_once_with("debate_prompt")


class TestProcessorPromptExtractorIntegration:
    """Test suite for CommentProcessor integration with PromptExtractor."""

    @pytest.fixture
    def temp_state_dir(self):
        """Create a temporary state directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def prompt_extractor(self, temp_state_dir):
        """Create a LocalDiskPromptExtractor."""
        from src.local_disk_prompt_extractor import LocalDiskPromptExtractor
        return LocalDiskPromptExtractor(state_dir=temp_state_dir)

    @pytest.fixture
    def mock_instagram_api(self):
        mock_api = MagicMock()
        mock_api.get_post_caption.return_value = "Test post caption"
        mock_api.get_comment_replies.return_value = []
        mock_api.post_reply.return_value = {"id": "reply_123"}
        return mock_api

    @pytest.fixture
    def mock_config(self):
        mock_cfg = MagicMock()
        mock_cfg.auto_post_enabled = False
        mock_cfg.articles_config = [
            {"path": "articles/test.md", "link": "https://example.com/test"}
        ]
        return mock_cfg

    def test_processor_accepts_prompt_extractor(
        self, mock_instagram_api, mock_config, prompt_extractor
    ):
        """Test that CommentProcessor can be constructed with a prompt_extractor."""
        from src.processor import CommentProcessor
        from src.prompt_extractor import PromptExtractor
        processor = CommentProcessor(
            mock_instagram_api,
            MagicMock(),
            None,
            mock_config,
            prompt_extractor=prompt_extractor
        )
        assert isinstance(processor.prompt_extractor, PromptExtractor)

    def test_processor_defaults_to_factory_prompt_extractor(
        self, mock_instagram_api, mock_config
    ):
        """Test that processor creates a prompt_extractor via factory when none provided."""
        from src.processor import CommentProcessor
        from src.prompt_extractor import PromptExtractor
        processor = CommentProcessor(
            mock_instagram_api,
            MagicMock(),
            None,
            mock_config
        )
        assert isinstance(processor.prompt_extractor, PromptExtractor)

    def test_processor_passes_prompt_extractor_to_llm_client(
        self, mock_instagram_api, mock_config, prompt_extractor
    ):
        """Test that CommentProcessor passes the prompt_extractor to llm_client."""
        from src.processor import CommentProcessor
        mock_llm = MagicMock()
        processor = CommentProcessor(
            mock_instagram_api,
            mock_llm,
            None,
            mock_config,
            prompt_extractor=prompt_extractor
        )
        # The llm_client.prompt_extractor should be set to the provided extractor
        assert mock_llm.prompt_extractor == prompt_extractor


class TestCompressConversationHistory:
    """Test suite for LLMClient.compress_conversation_history."""

    @pytest.fixture
    def mock_extractor(self):
        extractor = MagicMock()
        extractor.get_prompt.return_value = ""
        return extractor

    @pytest.fixture
    def llm_client(self, mock_extractor):
        from src.llm_client import LLMClient
        return LLMClient(
            api_key="test_key",
            model_name="test-model",
            prompt_extractor=mock_extractor,
        )

    def test_compress_conversation_history_returns_empty_when_no_context(self, llm_client):
        """compress_conversation_history returns empty string for empty thread context."""
        result = llm_client.compress_conversation_history("")
        assert result == ""

    def test_compress_conversation_history_calls_llm_with_template(self, llm_client, mock_extractor):
        """compress_conversation_history loads template and calls LLM with thread context."""
        template_content = "Compress this: {{THREAD_CONTEXT}}"
        mock_extractor.get_prompt.return_value = ""
        with patch("builtins.open", mock_open(read_data=template_content)):
            with patch.object(llm_client, "generate_response", return_value="- Arg A\n- Arg B") as mock_gen:
                result = llm_client.compress_conversation_history("@user1: some debate text")
        assert result == "- Arg A\n- Arg B"
        mock_gen.assert_called_once()

    def test_compress_conversation_history_uses_compress_history_template(self, llm_client, mock_extractor):
        """compress_conversation_history loads the compress_history_prompt template."""
        mock_extractor.get_prompt.return_value = ""
        with patch("builtins.open", mock_open(read_data="Compress: {{THREAD_CONTEXT}}")) as mock_file:
            with patch.object(llm_client, "generate_response", return_value="compressed"):
                llm_client.compress_conversation_history("some context")
        # Verify the file opened is the compress_history_prompt template
        opened_path = mock_file.call_args[0][0]
        assert "compress_history_prompt" in opened_path

    def test_compress_conversation_history_uses_stored_prompt_if_available(
        self, llm_client, mock_extractor
    ):
        """compress_conversation_history uses stored prompt from extractor when available."""
        mock_extractor.get_prompt.return_value = "Stored compress prompt: {{THREAD_CONTEXT}}"
        with patch.object(llm_client, "generate_response", return_value="stored result") as mock_gen:
            result = llm_client.compress_conversation_history("@user1: hello")
        assert result == "stored result"
        mock_gen.assert_called_once()
        # Ensure the stored prompt was used (extractor was consulted)
        mock_extractor.get_prompt.assert_called_with("compress_history_prompt")
