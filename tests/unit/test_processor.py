"""
Unit tests for comment processor.
"""
# pylint: disable=too-many-public-methods,line-too-long,too-many-arguments,too-many-positional-arguments
import json
import os
import shutil
import tempfile
from unittest.mock import Mock, MagicMock, patch, mock_open

import pytest

from src.processor import CommentProcessor


class TestCommentProcessor:
    """Test suite for CommentProcessor class."""

    @pytest.fixture
    def mock_instagram_api(self):
        """Create a mock Instagram API."""
        mock_api = Mock()
        mock_api.get_post_caption.return_value = "Test post caption"
        mock_api.get_comment_replies.return_value = []
        mock_api.post_reply.return_value = {"id": "reply_123"}
        return mock_api

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        mock_llm = Mock()
        mock_llm.check_post_topic_relevance.return_value = True
        mock_llm.check_comment_relevance.return_value = True
        mock_llm.load_template.return_value = "Template: {TOPIC} {FULL_ARTICLE_TEXT} {POST_CAPTION} {USERNAME} {COMMENT_TEXT} {THREAD_CONTEXT}"
        mock_llm.fill_template.return_value = "Filled template"
        mock_llm.generate_response.return_value = "Generated response with §1.1 citation"
        return mock_llm

    @pytest.fixture
    def mock_validator(self):
        """Create a mock response validator."""
        mock_val = Mock()
        mock_val.validate_response.return_value = (True, [])
        mock_val.extract_citations.return_value = ["§1.1"]
        return mock_val

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        mock_cfg = Mock()
        mock_cfg.auto_post_enabled = False
        mock_cfg.articles_config = [{"path": "articles/test.md", "link": "https://example.com/test"}]
        return mock_cfg

    @pytest.fixture
    def processor(self, mock_instagram_api, mock_llm_client, mock_validator, mock_config):
        """Create a CommentProcessor instance with mocked dependencies."""
        return CommentProcessor(
            mock_instagram_api,
            mock_llm_client,
            mock_validator,
            mock_config
        )

    @pytest.fixture
    def temp_state_dir(self):
        """Create a temporary state directory."""
        temp_dir = tempfile.mkdtemp()
        state_dir = os.path.join(temp_dir, "state")
        os.makedirs(state_dir, exist_ok=True)
        yield state_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_article(self):
        """Sample article content."""
        return """# Test Article

## §1. Introduction

### §1.1 Overview

This is a test article about fitness.

### §1.2 Details

Research shows that exercise is beneficial.
"""

    @pytest.fixture
    def sample_comment(self):
        """Sample comment data."""
        return {
            "comment_id": "comment_123",
            "post_id": "post_456",
            "username": "testuser",
            "text": "What do you think about this topic?"
        }

    def test_processor_initialization(self, processor, mock_instagram_api, mock_llm_client, mock_validator, mock_config):
        """Test that processor initializes properly with dependencies."""
        assert processor.instagram_api == mock_instagram_api
        assert processor.llm_client == mock_llm_client
        assert processor.validator == mock_validator
        assert processor.config == mock_config

    def test_load_article(self, processor):
        """Test loading article from file."""
        article_content = "# Test Article\n\nContent here."
        with patch("builtins.open", mock_open(read_data=article_content)):
            result = processor.load_article("articles/test.md")
            assert result == article_content

    def test_parse_article_metadata_with_title_and_summary(self, processor):
        """Test parsing article metadata with title and summary."""
        article_text = """# Article Title

## §1. Section One

This is the first paragraph summary.

More content here.
"""
        metadata = processor.parse_article_metadata(article_text)
        assert metadata["title"] == "Article Title"
        assert metadata["summary"] == "This is the first paragraph summary."

    def test_parse_article_metadata_no_title(self, processor):
        """Test parsing article without title."""
        article_text = """This is just content without a title.

More text here.
"""
        metadata = processor.parse_article_metadata(article_text)
        assert not metadata["title"]
        assert metadata["summary"] == "This is just content without a title."

    def test_parse_article_metadata_empty(self, processor):
        """Test parsing empty article."""
        article_text = ""
        metadata = processor.parse_article_metadata(article_text)
        assert not metadata["title"]
        assert not metadata["summary"]

    def test_load_pending_comments_file_exists(self, processor):
        """Test loading pending comments when file exists."""
        pending_data = {
            "version": "1.0",
            "comments": [
                {"comment_id": "c1", "text": "Comment 1"},
                {"comment_id": "c2", "text": "Comment 2"}
            ]
        }
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(pending_data))):
                comments = processor.load_pending_comments()
                assert len(comments) == 2
                assert comments[0]["comment_id"] == "c1"
                assert comments[1]["comment_id"] == "c2"

    def test_load_pending_comments_file_not_exists(self, processor):
        """Test loading pending comments when file doesn't exist."""
        with patch("os.path.exists", return_value=False):
            comments = processor.load_pending_comments()
            assert comments == []

    def test_process_comment_success(self, processor, sample_comment, sample_article, mock_instagram_api, mock_llm_client, mock_validator):  # pylint: disable=unused-argument
        """Test successful comment processing."""
        result = processor.process_comment(sample_comment, sample_article)

        assert result is not None
        assert result["comment_id"] == "comment_123"
        assert result["comment_text"] == "What do you think about this topic?"
        assert result["generated_response"] == "Generated response with §1.1 citation"
        assert result["citations_used"] == ["§1.1"]
        assert result["status"] == "pending_review"
        assert result["validation_passed"] is True
        assert result["validation_errors"] == []

        # Verify mocks were called
        mock_instagram_api.get_post_caption.assert_called_once_with("post_456")
        mock_llm_client.check_post_topic_relevance.assert_called_once()
        mock_llm_client.check_comment_relevance.assert_called_once()
        mock_llm_client.generate_response.assert_called_once()
        # Note: validator is now created internally, so we don't check mock_validator

    def test_process_comment_post_not_relevant(self, processor, sample_comment, sample_article, mock_llm_client):
        """Test processing when post is not relevant to article topic."""
        mock_llm_client.check_post_topic_relevance.return_value = False

        result = processor.process_comment(sample_comment, sample_article)

        assert result is None
        # Should not check comment relevance if post is not relevant
        mock_llm_client.check_comment_relevance.assert_not_called()

    def test_process_comment_comment_not_relevant(self, processor, sample_comment, sample_article, mock_llm_client):
        """Test processing when comment is not relevant."""
        mock_llm_client.check_comment_relevance.return_value = False

        with patch.object(processor, 'save_no_match_log') as mock_save:
            result = processor.process_comment(sample_comment, sample_article)

            assert result is None
            mock_save.assert_called_once_with(sample_comment, "Comment not relevant to article topic")

    def test_process_comment_validation_fails(self, processor, sample_comment, sample_article, mock_validator):  # pylint: disable=unused-argument
        """Test processing when validation fails."""
        # Mock LLM to generate response with invalid citation
        processor.llm_client.generate_response = Mock(return_value="Response with §9.9.9 invalid citation")
        
        result = processor.process_comment(sample_comment, sample_article)

        assert result is not None
        assert result["status"] == "failed"
        assert len(result["errors"]) > 0
        assert "§9.9.9" in result["errors"][0]

    def test_process_comment_api_exception(self, processor, sample_comment, sample_article, mock_instagram_api, mock_llm_client):
        """Test processing when Instagram API raises exception."""
        mock_instagram_api.get_post_caption.side_effect = Exception("API Error")

        # Should still process with empty post caption
        result = processor.process_comment(sample_comment, sample_article)

        assert result is not None
        # Should call check_comment_relevance even if get_post_caption fails
        mock_llm_client.check_comment_relevance.assert_called_once()

    def test_process_comment_auto_post_enabled(self, processor, sample_comment, sample_article, mock_config):
        """Test processing with auto-post enabled."""
        mock_config.auto_post_enabled = True

        result = processor.process_comment(sample_comment, sample_article)

        assert result is not None
        assert result["status"] == "approved"

    def test_build_thread_context_with_replies(self, processor, mock_instagram_api):
        """Test building thread context with replies."""
        mock_instagram_api.get_comment_replies.return_value = [
            {"from": {"username": "user1"}, "text": "Reply 1"},
            {"from": {"username": "user2"}, "text": "Reply 2"},
            {"from": {"username": "user3"}, "text": "Reply 3"}
        ]

        context = processor.build_thread_context("comment_123", "post_456")

        assert "@user1: Reply 1" in context
        assert "@user2: Reply 2" in context
        assert "@user3: Reply 3" in context
        mock_instagram_api.get_comment_replies.assert_called_once_with("comment_123")

    def test_build_thread_context_no_replies(self, processor, mock_instagram_api):
        """Test building thread context with no replies."""
        mock_instagram_api.get_comment_replies.return_value = []

        context = processor.build_thread_context("comment_123", "post_456")

        assert not context

    def test_build_thread_context_api_exception(self, processor, mock_instagram_api):
        """Test building thread context when API raises exception."""
        mock_instagram_api.get_comment_replies.side_effect = Exception("API Error")

        context = processor.build_thread_context("comment_123", "post_456")

        assert not context

    def test_build_thread_context_limits_to_five_replies(self, processor, mock_instagram_api):
        """Test that thread context limits to 5 most recent replies."""
        replies = [
            {"from": {"username": f"user{i}"}, "text": f"Reply {i}"}
            for i in range(10)
        ]
        mock_instagram_api.get_comment_replies.return_value = replies

        context = processor.build_thread_context("comment_123", "post_456")

        # Should only include first 5
        lines = context.split("\n")
        assert len(lines) == 5

    # pylint: disable=unused-argument
    def test_save_audit_log_new_file(self, processor, temp_state_dir):
        """Test saving audit log when file doesn't exist."""
        log_entry = {
            "comment_id": "comment_123",
            "status": "approved",
            "generated_response": "Test response"
        }

        with patch("os.makedirs"):
            with patch("os.path.exists", return_value=False):
                with patch("builtins.open", mock_open()) as _mock_file:
                    with patch("json.dump") as mock_json_dump:
                        processor.save_audit_log(log_entry)

                        # Check that entry was given an ID
                        call_args = mock_json_dump.call_args[0][0]
                        assert "entries" in call_args
                        assert len(call_args["entries"]) == 1
                        assert call_args["entries"][0]["id"] == "log_001"

    def test_save_audit_log_existing_file(self, processor):
        """Test saving audit log when file exists."""
        existing_data = {
            "version": "1.0",
            "entries": [
                {"id": "log_001", "comment_id": "old_comment"}
            ]
        }

        log_entry = {
            "comment_id": "comment_123",
            "status": "approved"
        }

        with patch("os.makedirs"):
            with patch("os.path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data=json.dumps(existing_data))) as _mock_file:
                    with patch("json.dump") as mock_json_dump:
                        processor.save_audit_log(log_entry)

                        # Check that entry was appended with correct ID
                        call_args = mock_json_dump.call_args[0][0]
                        assert len(call_args["entries"]) == 2
                        assert call_args["entries"][1]["id"] == "log_002"

    def test_save_no_match_log_new_file(self, processor):
        """Test saving no-match log when file doesn't exist."""
        comment = {
            "comment_id": "comment_123",
            "post_id": "post_456",
            "username": "testuser",
            "text": "Test comment"
        }

        with patch("os.makedirs"):
            with patch("os.path.exists", return_value=False):
                with patch("builtins.open", mock_open()) as _mock_file:
                    with patch("json.dump") as mock_json_dump:
                        processor.save_no_match_log(comment, "Not relevant")

                        call_args = mock_json_dump.call_args[0][0]
                        assert len(call_args["entries"]) == 1
                        entry = call_args["entries"][0]
                        assert entry["id"] == "nomatch_001"
                        assert entry["comment_id"] == "comment_123"
                        assert entry["reason"] == "Not relevant"

    def test_save_no_match_log_existing_file(self, processor):
        """Test saving no-match log when file exists."""
        existing_data = {
            "version": "1.0",
            "entries": [
                {"id": "nomatch_001", "comment_id": "old_comment"}
            ]
        }

        comment = {
            "comment_id": "comment_123",
            "post_id": "post_456",
            "username": "testuser",
            "text": "Test comment"
        }

        with patch("os.makedirs"):
            with patch("os.path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data=json.dumps(existing_data))):
                    with patch("json.dump") as mock_json_dump:
                        processor.save_no_match_log(comment, "Not relevant")

                        call_args = mock_json_dump.call_args[0][0]
                        assert len(call_args["entries"]) == 2
                        assert call_args["entries"][1]["id"] == "nomatch_002"

    def test_post_approved_responses_auto_post_disabled_with_approved(self, processor, mock_config, mock_instagram_api):
        """Test posting approved responses when auto-post is disabled.

        This test verifies that approved responses are posted even when AUTO_POST_ENABLED is false.
        This allows manually approved responses from the dashboard to be posted by the processor.
        """
        mock_config.auto_post_enabled = False

        # Mock the audit log extractor
        mock_entry = {
            "id": "log_001",
            "comment_id": "comment_123",
            "generated_response": "Test response",
            "status": "approved",
            "posted": False
        }
        
        processor.audit_log_extractor.load_entries = Mock(return_value=[mock_entry])
        processor.audit_log_extractor.update_entry = Mock()
        
        processor.post_approved_responses()

        # Should post approved responses even when auto-post is disabled
        mock_instagram_api.post_reply.assert_called_once_with("comment_123", "Test response")
        
        # Verify update_entry was called with correct data
        processor.audit_log_extractor.update_entry.assert_called_once()
        call_args = processor.audit_log_extractor.update_entry.call_args[0]
        assert call_args[0] == "log_001"  # entry_id
        assert call_args[1]["posted"] is True  # updates
        assert "posted_at" in call_args[1]

    def test_post_approved_responses_no_audit_file(self, processor, mock_config):
        """Test posting responses when audit file doesn't exist."""
        # AUTO_POST_ENABLED setting should not matter here
        mock_config.auto_post_enabled = True

        # Mock the audit log extractor returning empty list (no entries)
        processor.audit_log_extractor.load_entries = Mock(return_value=[])
        
        processor.post_approved_responses()

        processor.instagram_api.post_reply.assert_not_called()

    def test_post_approved_responses_success(self, processor, mock_config, mock_instagram_api):
        """Test successfully posting approved responses.

        AUTO_POST_ENABLED should not affect posting of already approved responses.
        """
        # Set to False to emphasize that AUTO_POST_ENABLED doesn't affect approved response posting
        mock_config.auto_post_enabled = False

        # Mock the audit log extractor with two entries
        mock_entries = [
            {
                "id": "log_001",
                "comment_id": "comment_123",
                "generated_response": "Test response",
                "status": "approved",
                "posted": False
            },
            {
                "id": "log_002",
                "comment_id": "comment_456",
                "generated_response": "Another response",
                "status": "pending_review",
                "posted": False
            }
        ]
        
        processor.audit_log_extractor.load_entries = Mock(return_value=mock_entries)
        processor.audit_log_extractor.update_entry = Mock()
        
        processor.post_approved_responses()

        # Should only post the approved one
        mock_instagram_api.post_reply.assert_called_once_with("comment_123", "Test response")
        
        # Verify update_entry was called once for the approved entry
        processor.audit_log_extractor.update_entry.assert_called_once()
        call_args = processor.audit_log_extractor.update_entry.call_args[0]
        assert call_args[0] == "log_001"  # entry_id
        assert call_args[1]["posted"] is True  # updates
        assert "posted_at" in call_args[1]

    def test_post_approved_responses_already_posted(self, processor, mock_config, mock_instagram_api):
        """Test posting responses when already posted."""
        # AUTO_POST_ENABLED should not matter for already posted responses
        mock_config.auto_post_enabled = False

        # Mock the audit log extractor with already posted entry
        mock_entry = {
            "id": "log_001",
            "comment_id": "comment_123",
            "generated_response": "Test response",
            "status": "approved",
            "posted": True
        }
        
        processor.audit_log_extractor.load_entries = Mock(return_value=[mock_entry])
        
        processor.post_approved_responses()

        # Should not post again
        mock_instagram_api.post_reply.assert_not_called()

    def test_post_approved_responses_api_exception(self, processor, mock_config, mock_instagram_api):
        """Test posting responses when API raises exception."""
        # AUTO_POST_ENABLED should not affect error handling
        mock_config.auto_post_enabled = False
        mock_instagram_api.post_reply.side_effect = Exception("API Error")

        # Mock the audit log extractor
        mock_entry = {
            "id": "log_001",
            "comment_id": "comment_123",
            "generated_response": "Test response",
            "status": "approved",
            "posted": False
        }
        
        processor.audit_log_extractor.load_entries = Mock(return_value=[mock_entry])
        processor.audit_log_extractor.update_entry = Mock()
        
        processor.post_approved_responses()

        # Check that error was recorded via update_entry
        processor.audit_log_extractor.update_entry.assert_called_once()
        call_args = processor.audit_log_extractor.update_entry.call_args[0]
        assert call_args[0] == "log_001"  # entry_id
        assert "post_error" in call_args[1]  # updates
        # Error should now be a structured dict with "message" key
        assert isinstance(call_args[1]["post_error"], dict)
        assert call_args[1]["post_error"]["message"] == "API Error"

    def test_extract_graph_api_error_with_response_json(self, processor):
        """Test extracting error from exception with response.json() method."""
        # Create mock exception with response that has json() method
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": {
                "code": 100,
                "message": "Invalid parameter",
                "error_subcode": 1234
            }
        }
        
        exc = Exception("API Error")
        exc.response = mock_response
        
        result = processor._extract_graph_api_error(exc)
        
        assert result is not None
        assert result["error"]["code"] == 100
        assert result["error"]["message"] == "Invalid parameter"

    def test_extract_graph_api_error_with_response_text(self, processor):
        """Test extracting error from exception with response.text as JSON."""
        # Create mock exception with response that has text attribute
        mock_response = Mock()
        mock_response.json.side_effect = Exception("Cannot parse")
        mock_response.text = '{"error": {"code": 200, "message": "Rate limit"}}'
        
        exc = Exception("API Error")
        exc.response = mock_response
        
        result = processor._extract_graph_api_error(exc)
        
        assert result is not None
        assert result["error"]["code"] == 200
        assert result["error"]["message"] == "Rate limit"

    def test_extract_graph_api_error_with_response_text_non_json(self, processor):
        """Test extracting error from exception with response.text as plain text."""
        # Create mock exception with response that has non-JSON text
        mock_response = Mock()
        mock_response.json.side_effect = Exception("Cannot parse")
        mock_response.text = "Server error occurred"
        
        exc = Exception("API Error")
        exc.response = mock_response
        
        result = processor._extract_graph_api_error(exc)
        
        assert result is not None
        assert result["text"] == "Server error occurred"

    def test_extract_graph_api_error_with_dict_in_args(self, processor):
        """Test extracting error from exception with dict in args."""
        error_dict = {"code": 300, "message": "Permission denied"}
        exc = Exception(error_dict)
        
        result = processor._extract_graph_api_error(exc)
        
        assert result is not None
        assert result["code"] == 300
        assert result["message"] == "Permission denied"

    def test_extract_graph_api_error_with_json_string_in_args(self, processor):
        """Test extracting error from exception with JSON string in args."""
        exc = Exception('{"error": "Invalid token"}')
        
        result = processor._extract_graph_api_error(exc)
        
        assert result is not None
        assert result["error"] == "Invalid token"

    def test_extract_graph_api_error_with_bytes_in_args(self, processor):
        """Test extracting error from exception with bytes in args."""
        exc = Exception(b'{"error": "Bytes error"}')
        
        result = processor._extract_graph_api_error(exc)
        
        assert result is not None
        assert result["error"] == "Bytes error"

    def test_extract_graph_api_error_with_body_attribute(self, processor):
        """Test extracting error from exception with body attribute."""
        exc = Exception("API Error")
        exc.body = {"error_code": 400, "error_msg": "Bad request"}
        
        result = processor._extract_graph_api_error(exc)
        
        assert result is not None
        assert result["error_code"] == 400
        assert result["error_msg"] == "Bad request"

    def test_extract_graph_api_error_with_result_attribute(self, processor):
        """Test extracting error from exception with result attribute."""
        exc = Exception("API Error")
        exc.result = '{"status": "error", "details": "Not found"}'
        
        result = processor._extract_graph_api_error(exc)
        
        assert result is not None
        assert result["status"] == "error"
        assert result["details"] == "Not found"

    def test_extract_graph_api_error_with_error_data_attribute(self, processor):
        """Test extracting error from exception with error_data attribute."""
        exc = Exception("API Error")
        exc.error_data = ["error1", "error2"]
        
        result = processor._extract_graph_api_error(exc)
        
        assert result is not None
        assert result == ["error1", "error2"]

    def test_extract_graph_api_error_no_data(self, processor):
        """Test extracting error from exception with no extractable data."""
        exc = Exception("Simple error message")
        
        result = processor._extract_graph_api_error(exc)
        
        # Should return None when no extractable data found
        assert result is None

    def test_extract_graph_api_error_extraction_fails(self, processor):
        """Test extracting error when extraction itself raises exception."""
        # Create an exception with a response attribute that raises when accessed
        exc = Exception("API Error")
        
        # Create a mock response where accessing text raises an exception
        class BadResponse:
            @property
            def json(self):
                raise RuntimeError("Cannot call json()")
            
            @property
            def text(self):
                raise RuntimeError("Cannot access text")
        
        exc.response = BadResponse()
        
        result = processor._extract_graph_api_error(exc)
        
        # Should return error extraction failure message
        assert result is not None
        assert "error_extraction_failed" in result

    def test_post_approved_responses_with_graph_api_error(self, processor, mock_config, mock_instagram_api):
        """Test posting responses when API raises exception with Graph API error details."""
        mock_config.auto_post_enabled = False
        
        # Create exception with Graph API error response
        mock_response = Mock()
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid OAuth token",
                "code": 190,
                "error_subcode": 463,
                "error_user_title": "Token Expired",
                "error_user_msg": "Please refresh your access token"
            }
        }
        
        exc = Exception("Graph API Error")
        exc.response = mock_response
        mock_instagram_api.post_reply.side_effect = exc

        # Mock the audit log extractor
        mock_entry = {
            "id": "log_001",
            "comment_id": "comment_123",
            "generated_response": "Test response",
            "status": "approved",
            "posted": False
        }
        
        processor.audit_log_extractor.load_entries = Mock(return_value=[mock_entry])
        processor.audit_log_extractor.update_entry = Mock()
        
        processor.post_approved_responses()

        # Check that structured error was recorded
        processor.audit_log_extractor.update_entry.assert_called_once()
        call_args = processor.audit_log_extractor.update_entry.call_args[0]
        assert call_args[0] == "log_001"
        error_payload = call_args[1]["post_error"]
        
        # Verify structured payload
        assert isinstance(error_payload, dict)
        assert error_payload["message"] == "Graph API Error"
        assert "graph_api_error" in error_payload
        assert error_payload["graph_api_error"]["error"]["code"] == 190
        assert error_payload["graph_api_error"]["error"]["error_subcode"] == 463

    def test_clear_pending_comments_file_exists(self, processor):
        """Test clearing pending comments when file exists."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open()) as _mock_file:
                with patch("json.dump") as mock_json_dump:
                    processor.clear_pending_comments()

                    # Check that file was cleared
                    call_args = mock_json_dump.call_args[0][0]
                    assert call_args["version"] == "1.0"
                    assert call_args["comments"] == []

    def test_clear_pending_comments_file_not_exists(self, processor):
        """Test clearing pending comments when file doesn't exist."""
        with patch("os.path.exists", return_value=False):
            # Should handle gracefully without error
            processor.clear_pending_comments()

    def test_run_no_comments(self, processor, sample_article, capsys):
        """Test run method with no pending comments.
        
        Even when there are no pending comments to process, the run method should
        still call post_approved_responses to handle any previously approved responses.
        """
        with patch.object(processor, 'load_article', return_value=sample_article):
            with patch.object(processor, 'load_pending_comments', return_value=[]):
                with patch.object(processor, 'post_approved_responses') as mock_post:
                    processor.run()

                    captured = capsys.readouterr()
                    assert "No pending comments to process" in captured.out
                    # Should still call post_approved_responses for any manually approved responses
                    mock_post.assert_called_once()

    def test_run_no_pending_comments_but_approved_responses_exist(self, processor, sample_article, mock_instagram_api, capsys):
        """Test run method when no pending comments but approved responses exist.
        
        This tests the specific bug fix: when there are no pending comments,
        the processor should still post any approved responses that are waiting.
        """
        # Setup approved response waiting to be posted
        approved_entry = {
            "id": "audit_001",
            "comment_id": "comment_123",
            "generated_response": "Test response",
            "status": "approved",
            "posted": False
        }
        
        with patch.object(processor, 'load_article', return_value=sample_article):
            with patch.object(processor, 'load_pending_comments', return_value=[]):
                # Mock the audit log to return an approved response
                processor.audit_log_extractor.load_entries = Mock(return_value=[approved_entry])
                processor.audit_log_extractor.update_entry = Mock()
                
                # Mock the Instagram API
                mock_instagram_api.post_reply.return_value = {"id": "reply_123"}
                
                processor.run()

                captured = capsys.readouterr()
                assert "No pending comments to process" in captured.out
                assert "Posting approved responses" in captured.out
                # Verify the approved response was posted
                mock_instagram_api.post_reply.assert_called_once_with(
                    "comment_123",
                    "Test response"
                )

    def test_run_with_comments_but_no_articles_configured(self, processor, sample_comment, mock_config, capsys):
        """Test run method when pending comments exist but no articles are configured.
        
        When articles are not configured, pending comments cannot be processed,
        but approved responses should still be posted. Pending comments should
        NOT be cleared since they weren't processed.
        """
        mock_config.articles_config = []  # No articles configured
        comments = [sample_comment]

        with patch.object(processor, 'load_pending_comments', return_value=comments):
            with patch.object(processor, 'post_approved_responses') as mock_post:
                with patch.object(processor, 'clear_pending_comments') as mock_clear:
                    processor.run()

                    captured = capsys.readouterr()
                    assert "Processing 1 pending comment(s)" in captured.out
                    assert "No articles configured" in captured.out
                    # Should still post approved responses
                    mock_post.assert_called_once()
                    # Should NOT clear pending comments since we didn't process them
                    mock_clear.assert_not_called()

    def test_run_with_comments(self, processor, sample_article, sample_comment, capsys):
        """Test run method with pending comments."""
        comments = [sample_comment]

        with patch.object(processor, 'load_article', return_value=sample_article):
            with patch.object(processor, 'load_pending_comments', return_value=comments):
                with patch.object(processor, 'process_comment', return_value={
                    "comment_id": "comment_123",
                    "status": "pending_review"
                }):
                    with patch.object(processor, 'save_audit_log'):
                        with patch.object(processor, 'post_approved_responses') as mock_post:
                            with patch.object(processor, 'clear_pending_comments'):
                                processor.run()

                                captured = capsys.readouterr()
                                assert "Processing 1 pending comment(s)" in captured.out
                                assert "Generated response" in captured.out
                                # Should always call post_approved_responses
                                mock_post.assert_called_once()

    def test_run_with_skipped_comment(self, processor, sample_article, sample_comment, capsys):
        """Test run method with skipped comment."""
        comments = [sample_comment]

        with patch.object(processor, 'load_article', return_value=sample_article):
            with patch.object(processor, 'load_pending_comments', return_value=comments):
                with patch.object(processor, 'process_comment', return_value=None):
                    with patch.object(processor, 'post_approved_responses') as mock_post:
                        with patch.object(processor, 'clear_pending_comments'):
                            processor.run()

                            captured = capsys.readouterr()
                            assert "Skipped (not relevant)" in captured.out
                            # Should still call post_approved_responses
                            mock_post.assert_called_once()

    def test_run_with_auto_post_enabled(self, processor, sample_article, sample_comment, mock_config, capsys):
        """Test run method with auto-post enabled.

        When AUTO_POST_ENABLED is true, responses should be auto-approved and then posted.
        """
        mock_config.auto_post_enabled = True
        comments = [sample_comment]

        with patch.object(processor, 'load_article', return_value=sample_article):
            with patch.object(processor, 'load_pending_comments', return_value=comments):
                with patch.object(processor, 'process_comment', return_value={
                    "comment_id": "comment_123",
                    "status": "approved"
                }):
                    with patch.object(processor, 'save_audit_log'):
                        with patch.object(processor, 'post_approved_responses') as mock_post:
                            with patch.object(processor, 'clear_pending_comments'):
                                processor.run()

                                captured = capsys.readouterr()
                                assert "Posting approved responses" in captured.out
                                mock_post.assert_called_once()

    def test_run_with_auto_post_disabled(self, processor, sample_article, sample_comment, mock_config, capsys):
        """Test run method with auto-post disabled.

        When AUTO_POST_ENABLED is false, responses should go to pending_review,
        but post_approved_responses should still be called to post any manually approved responses.
        """
        mock_config.auto_post_enabled = False
        comments = [sample_comment]

        with patch.object(processor, 'load_article', return_value=sample_article):
            with patch.object(processor, 'load_pending_comments', return_value=comments):
                with patch.object(processor, 'process_comment', return_value={
                    "comment_id": "comment_123",
                    "status": "pending_review"
                }):
                    with patch.object(processor, 'save_audit_log'):
                        with patch.object(processor, 'post_approved_responses') as mock_post:
                            with patch.object(processor, 'clear_pending_comments'):
                                processor.run()

                                captured = capsys.readouterr()
                                assert "Posting approved responses" in captured.out
                                # Should still call post_approved_responses
                                mock_post.assert_called_once()

    def test_load_articles_single(self, processor):
        """Test loading multiple articles when one article is configured."""
        articles_config = [
            {"path": "articles/article1.md", "link": "https://example.com/article1"}
        ]
        article_content = "# Article 1\n\nContent here."

        with patch("builtins.open", mock_open(read_data=article_content)):
            articles = processor.load_articles(articles_config)

            assert len(articles) == 1
            assert articles[0]["path"] == "articles/article1.md"
            assert articles[0]["link"] == "https://example.com/article1"
            assert articles[0]["content"] == article_content

    def test_load_articles_multiple(self, processor):
        """Test loading multiple articles."""
        articles_config = [
            {"path": "articles/article1.md", "link": "https://example.com/article1"},
            {"path": "articles/article2.md", "link": "https://example.com/article2"}
        ]

        def mock_open_multiple(filename, *args, **kwargs):
            """Mock open to return different content based on filename."""
            if "article1.md" in filename:
                return mock_open(read_data="# Article 1\n\nContent 1.")()
            if "article2.md" in filename:
                return mock_open(read_data="# Article 2\n\nContent 2.")()
            return mock_open(read_data="")()

        with patch("builtins.open", side_effect=mock_open_multiple):
            articles = processor.load_articles(articles_config)

            assert len(articles) == 2
            assert "Article 1" in articles[0]["content"]
            assert "Article 2" in articles[1]["content"]

    def test_select_relevant_article_single_match(self, processor, sample_comment, mock_llm_client):
        """Test selecting relevant article when one article matches."""
        articles = [
            {
                "path": "articles/article1.md",
                "link": "https://example.com/article1",
                "content": "# Article 1\n\nAbout fitness.",
                "title": "Article 1",
                "summary": "About fitness."
            },
            {
                "path": "articles/article2.md",
                "link": "https://example.com/article2",
                "content": "# Article 2\n\nAbout nutrition.",
                "title": "Article 2",
                "summary": "About nutrition."
            }
        ]

        # Mock to return True for first article, False for second
        mock_llm_client.check_topic_relevance.side_effect = [True, False]

        selected = processor.select_relevant_article(
            articles,
            "Post about fitness",
            sample_comment["text"],
            ""
        )

        assert selected is not None
        assert selected["title"] == "Article 1"

    def test_select_relevant_article_no_match(self, processor, sample_comment, mock_llm_client):
        """Test selecting relevant article when no articles match."""
        articles = [
            {
                "path": "articles/article1.md",
                "link": "https://example.com/article1",
                "content": "# Article 1\n\nContent.",
                "title": "Article 1",
                "summary": "Content."
            }
        ]

        mock_llm_client.check_topic_relevance.return_value = False

        selected = processor.select_relevant_article(
            articles,
            "Post caption",
            sample_comment["text"],
            ""
        )

        assert selected is None

    def test_select_relevant_article_first_match_wins(self, processor, sample_comment, mock_llm_client):
        """Test that first matching article is selected when multiple match."""
        articles = [
            {
                "path": "articles/article1.md",
                "link": "https://example.com/article1",
                "content": "# Article 1\n\nContent 1.",
                "title": "Article 1",
                "summary": "Content 1."
            },
            {
                "path": "articles/article2.md",
                "link": "https://example.com/article2",
                "content": "# Article 2\n\nContent 2.",
                "title": "Article 2",
                "summary": "Content 2."
            }
        ]

        # Both return True
        mock_llm_client.check_topic_relevance.return_value = True

        selected = processor.select_relevant_article(
            articles,
            "Post caption",
            sample_comment["text"],
            ""
        )

        # Should select first one
        assert selected is not None
        assert selected["title"] == "Article 1"

    def test_process_comment_multi_article_with_selection(self, processor, sample_comment, mock_llm_client, mock_validator):  # pylint: disable=unused-argument
        """Test processing comment with multiple articles and article selection."""
        # Note: Article content includes §1.1 subsection to match the citation
        # generated by mock_llm_client ("Generated response with §1.1 citation")
        articles = [
            {
                "path": "articles/article1.md",
                "link": "https://example.com/article1",
                "content": "# Article 1\n\n## §1. Section\n\n### §1.1 Subsection\n\nFitness content.",
                "title": "Article 1",
                "summary": "Fitness content."
            }
        ]

        # Mock article selection to return the article
        with patch.object(processor, 'select_relevant_article', return_value=articles[0]):
            result = processor.process_comment_multi_article(sample_comment, articles)

            assert result is not None
            assert result["comment_id"] == "comment_123"
            assert "article_used" in result
            assert result["article_used"]["path"] == "articles/article1.md"

    def test_process_comment_multi_article_no_match(self, processor, sample_comment, mock_llm_client):
        """Test processing comment when no article matches."""
        articles = [
            {
                "path": "articles/article1.md",
                "link": "https://example.com/article1",
                "content": "# Article 1\n\nContent.",
                "title": "Article 1",
                "summary": "Content."
            }
        ]

        # Mock article selection to return None
        with patch.object(processor, 'select_relevant_article', return_value=None):
            with patch.object(processor, 'save_no_match_log') as mock_save:
                result = processor.process_comment_multi_article(sample_comment, articles)

                assert result is None
                mock_save.assert_called_once()

    def test_run_multi_article(self, processor, sample_comment, mock_config, capsys):
        """Test run method with multiple articles configured."""
        articles_config = [
            {"path": "articles/article1.md", "link": "https://example.com/article1"},
            {"path": "articles/article2.md", "link": "https://example.com/article2"}
        ]
        mock_config.articles_config = articles_config

        articles = [
            {
                "path": "articles/article1.md",
                "link": "https://example.com/article1",
                "content": "# Article 1\n\nContent.",
                "title": "Article 1",
                "summary": "Content."
            }
        ]

        comments = [sample_comment]

        with patch.object(processor, 'load_articles', return_value=articles):
            with patch.object(processor, 'load_pending_comments', return_value=comments):
                with patch.object(processor, 'process_comment_multi_article', return_value={
                    "comment_id": "comment_123",
                    "status": "pending_review"
                }):
                    with patch.object(processor, 'save_audit_log'):
                        with patch.object(processor, 'post_approved_responses'):
                            with patch.object(processor, 'clear_pending_comments'):
                                processor.run()

                                captured = capsys.readouterr()
                                assert "Processing 1 pending comment(s)" in captured.out

    def test_ensure_valid_token_oauth_token_fresh(self, processor, capsys):
        """Test _ensure_valid_token when OAuth token is fresh."""
        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = {
                "access_token": "fresh_oauth_token",
                "expires_at": "2026-03-30T00:00:00Z"
            }
            mock_extractor.is_token_expired.return_value = False
            mock_factory.return_value = mock_extractor
            
            processor._ensure_valid_token()
            
            captured = capsys.readouterr()
            assert "OAuth token is valid" in captured.out
            mock_extractor.is_token_expired.assert_called_once_with(buffer_days=5)

    def test_ensure_valid_token_oauth_token_refreshed(self, processor, mock_config, capsys):
        """Test _ensure_valid_token refreshes expiring OAuth token."""
        mock_config.instagram_app_secret = "test_secret"
        
        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = {
                "access_token": "expiring_oauth_token",
                "expires_at": "2026-02-20T00:00:00Z"
            }
            mock_extractor.is_token_expired.return_value = True
            mock_extractor.refresh_token.return_value = True
            mock_factory.return_value = mock_extractor
            
            processor._ensure_valid_token()
            
            captured = capsys.readouterr()
            assert "Token expiring soon" in captured.out
            assert "Token refreshed successfully" in captured.out
            mock_extractor.refresh_token.assert_called_once_with("test_secret")

    def test_ensure_valid_token_refresh_fails(self, processor, mock_config, capsys):
        """Test _ensure_valid_token when token refresh fails."""
        mock_config.instagram_app_secret = "test_secret"
        
        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = {
                "access_token": "expiring_oauth_token",
                "expires_at": "2026-02-20T00:00:00Z"
            }
            mock_extractor.is_token_expired.return_value = True
            mock_extractor.refresh_token.return_value = False
            mock_factory.return_value = mock_extractor
            
            processor._ensure_valid_token()
            
            captured = capsys.readouterr()
            assert "Token refresh failed" in captured.out

    def test_ensure_valid_token_no_oauth(self, processor, capsys):
        """Test _ensure_valid_token when no OAuth token exists."""
        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_extractor = MagicMock()
            mock_extractor.get_token.return_value = None
            mock_factory.return_value = mock_extractor
            
            processor._ensure_valid_token()
            
            captured = capsys.readouterr()
            assert "No OAuth token found" in captured.out

    def test_ensure_valid_token_handles_exception(self, processor, capsys):
        """Test _ensure_valid_token handles exceptions gracefully."""
        with patch('src.token_extractor_factory.create_token_extractor') as mock_factory:
            mock_factory.side_effect = Exception("Token extractor error")
            
            processor._ensure_valid_token()
            
            captured = capsys.readouterr()
            assert "Token validation warning" in captured.out

    def test_post_approved_responses_calls_token_validation(self, processor, mock_config, mock_instagram_api):
        """Test that post_approved_responses calls token validation."""
        with patch.object(processor, '_ensure_valid_token') as mock_token_check:
            with patch.object(processor.audit_log_extractor, 'load_entries', return_value=[]):
                processor.post_approved_responses()
                
                # Should call token validation before posting
                mock_token_check.assert_called_once()

    def test_run_skips_own_comments_single_article(self, processor, sample_article, mock_config, capsys):
        """Test that the processor skips comments from its own Instagram account (single-article mode)."""
        mock_config.instagram_username = "mybotaccount"
        mock_config.articles_config = [{"path": "articles/test.md", "link": "https://example.com/test"}]

        own_comment = {
            "comment_id": "comment_own_1",
            "post_id": "post_456",
            "username": "mybotaccount",
            "text": "A reply I posted myself"
        }
        other_comment = {
            "comment_id": "comment_other_1",
            "post_id": "post_456",
            "username": "someotheruser",
            "text": "A comment from another user"
        }
        comments = [own_comment, other_comment]

        with patch.object(processor, 'load_article', return_value=sample_article):
            with patch.object(processor, 'load_pending_comments', return_value=comments):
                with patch.object(processor, 'process_comment') as mock_process:
                    mock_process.return_value = {"comment_id": "comment_other_1", "status": "pending_review"}
                    with patch.object(processor, 'save_audit_log'):
                        with patch.object(processor, 'post_approved_responses'):
                            with patch.object(processor, 'clear_pending_comments'):
                                processor.run()

                                # process_comment should be called only for the non-own comment
                                assert mock_process.call_count == 1
                                call_comment = mock_process.call_args[0][0]
                                assert call_comment["comment_id"] == "comment_other_1"

    def test_run_skips_own_comments_multi_article(self, processor, mock_config, capsys):
        """Test that the processor skips comments from its own Instagram account (multi-article mode)."""
        mock_config.instagram_username = "mybotaccount"
        articles_config = [
            {"path": "articles/article1.md", "link": "https://example.com/article1"},
            {"path": "articles/article2.md", "link": "https://example.com/article2"}
        ]
        mock_config.articles_config = articles_config

        own_comment = {
            "comment_id": "comment_own_2",
            "post_id": "post_456",
            "username": "mybotaccount",
            "text": "My own reply"
        }
        other_comment = {
            "comment_id": "comment_other_2",
            "post_id": "post_456",
            "username": "anotheruser",
            "text": "Another user comment"
        }
        comments = [own_comment, other_comment]

        articles = [
            {
                "path": "articles/article1.md",
                "link": "https://example.com/article1",
                "content": "# Article 1\n\nContent.",
                "title": "Article 1",
                "summary": "Content."
            }
        ]

        with patch.object(processor, 'load_articles', return_value=articles):
            with patch.object(processor, 'load_pending_comments', return_value=comments):
                with patch.object(processor, 'process_comment_multi_article') as mock_process:
                    mock_process.return_value = {"comment_id": "comment_other_2", "status": "pending_review"}
                    with patch.object(processor, 'save_audit_log'):
                        with patch.object(processor, 'post_approved_responses'):
                            with patch.object(processor, 'clear_pending_comments'):
                                processor.run()

                                # process_comment_multi_article should be called only for the non-own comment
                                assert mock_process.call_count == 1
                                call_comment = mock_process.call_args[0][0]
                                assert call_comment["comment_id"] == "comment_other_2"

    def test_run_own_comment_filtering_case_insensitive(self, processor, sample_article, mock_config, capsys):
        """Test that own-comment filtering in the processor is case-insensitive."""
        mock_config.instagram_username = "MyBotAccount"
        mock_config.articles_config = [{"path": "articles/test.md", "link": "https://example.com/test"}]

        own_comment = {
            "comment_id": "comment_own_3",
            "post_id": "post_456",
            "username": "mybotaccount",  # lowercase, should still match
            "text": "My own reply"
        }

        with patch.object(processor, 'load_article', return_value=sample_article):
            with patch.object(processor, 'load_pending_comments', return_value=[own_comment]):
                with patch.object(processor, 'process_comment') as mock_process:
                    with patch.object(processor, 'post_approved_responses'):
                        with patch.object(processor, 'clear_pending_comments'):
                            processor.run()

                            # Should not process own comment
                            mock_process.assert_not_called()


class TestCommentProcessorUnnumbered:
    """Test suite for CommentProcessor with unnumbered articles."""

    @pytest.fixture
    def mock_instagram_api(self):
        """Create a mock Instagram API."""
        mock_api = Mock()
        mock_api.get_post_caption.return_value = "Test post caption"
        mock_api.get_comment_replies.return_value = []
        mock_api.post_reply.return_value = {"id": "reply_123"}
        return mock_api

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        mock_llm = Mock()
        mock_llm.check_post_topic_relevance.return_value = True
        mock_llm.check_comment_relevance.return_value = True
        mock_llm.check_topic_relevance.return_value = True
        mock_llm.load_template.return_value = "Template: {TOPIC} {FULL_ARTICLE_TEXT}"
        mock_llm.fill_template.return_value = "Filled template"
        mock_llm.generate_response.return_value = "Generated response without citations"
        return mock_llm

    @pytest.fixture
    def mock_validator(self):
        """Create a mock response validator."""
        mock_val = Mock()
        mock_val.validate_response.return_value = (True, [])
        mock_val.extract_citations.return_value = []
        return mock_val

    @pytest.fixture
    def mock_config(self):
        """Create a mock config with unnumbered article."""
        mock_cfg = Mock()
        mock_cfg.auto_post_enabled = False
        mock_cfg.articles_config = [{
            "path": "articles_unnumbered/test.md",
            "link": "https://example.com/test",
            "is_numbered": False
        }]
        return mock_cfg

    @pytest.fixture
    def processor(self, mock_instagram_api, mock_llm_client, mock_validator, mock_config):
        """Create a CommentProcessor instance with mocked dependencies."""
        return CommentProcessor(
            mock_instagram_api,
            mock_llm_client,
            mock_validator,
            mock_config
        )

    @pytest.fixture
    def sample_unnumbered_article(self):
        """Sample unnumbered article content."""
        return """# General Fitness Guidelines

Regular physical activity is beneficial for health.

## Benefits

Exercise helps with weight management and reduces disease risk.
"""

    @pytest.fixture
    def sample_comment(self):
        """Sample comment data."""
        return {
            "comment_id": "comment_123",
            "post_id": "post_456",
            "username": "testuser",
            "text": "What do you think about exercise?"
        }

    def test_load_articles_with_is_numbered_flag(self, processor):
        """Test loading articles with is_numbered flag."""
        articles_config = [
            {
                "path": "articles_unnumbered/test.md",
                "link": "https://example.com/test",
                "is_numbered": False
            }
        ]

        article_content = "# Test Article\n\nContent without numbered sections."

        with patch.object(processor, 'load_article', return_value=article_content):
            articles = processor.load_articles(articles_config)

            assert len(articles) == 1
            assert articles[0]["is_numbered"] is False
            assert articles[0]["path"] == "articles_unnumbered/test.md"

    def test_process_comment_multi_article_unnumbered(
        self, processor, sample_comment, sample_unnumbered_article,
        mock_llm_client, mock_validator  # pylint: disable=unused-argument
    ):
        """Test processing comment with unnumbered article."""
        articles = [{
            "path": "articles_unnumbered/test.md",
            "link": "https://example.com/test",
            "content": sample_unnumbered_article,
            "title": "General Fitness Guidelines",
            "summary": "Regular physical activity is beneficial for health.",
            "is_numbered": False
        }]

        result = processor.process_comment_multi_article(sample_comment, articles)

        assert result is not None
        assert result["comment_id"] == "comment_123"
        assert result["status"] in ["approved", "pending_review"]
        # Citations should be empty for unnumbered articles (no citations in generated response)
        assert result["citations_used"] == []


class TestCommentProcessorArticleExtractor:
    """Tests for CommentProcessor article extractor integration."""

    @pytest.fixture
    def mock_instagram_api(self):
        mock_api = Mock()
        mock_api.get_post_caption.return_value = "Test post caption"
        mock_api.get_comment_replies.return_value = []
        mock_api.post_reply.return_value = {"id": "reply_123"}
        return mock_api

    @pytest.fixture
    def mock_llm_client(self):
        mock_llm = Mock()
        mock_llm.check_post_topic_relevance.return_value = True
        mock_llm.check_comment_relevance.return_value = True
        mock_llm.check_topic_relevance.return_value = True
        mock_llm.load_template.return_value = "Template: {TOPIC} {FULL_ARTICLE_TEXT} {POST_CAPTION} {USERNAME} {COMMENT_TEXT} {THREAD_CONTEXT}"
        mock_llm.fill_template.return_value = "Filled template"
        mock_llm.generate_response.return_value = "Generated response with §1.1 citation"
        return mock_llm

    @pytest.fixture
    def mock_validator(self):
        mock_val = Mock()
        mock_val.validate_response.return_value = (True, [])
        mock_val.extract_citations.return_value = ["§1.1"]
        return mock_val

    @pytest.fixture
    def mock_config(self):
        mock_cfg = Mock()
        mock_cfg.auto_post_enabled = False
        mock_cfg.instagram_username = ""
        mock_cfg.articles_config = [{"path": "articles/test.md", "link": "https://example.com/test"}]
        return mock_cfg

    @pytest.fixture
    def mock_article_extractor(self):
        ext = Mock()
        ext.get_articles.return_value = []
        return ext

    @pytest.fixture
    def processor(self, mock_instagram_api, mock_llm_client, mock_validator, mock_config, mock_article_extractor):
        return CommentProcessor(
            mock_instagram_api,
            mock_llm_client,
            mock_validator,
            mock_config,
            article_extractor=mock_article_extractor,
        )

    @pytest.fixture
    def sample_comment(self):
        return {
            "comment_id": "comment_123",
            "post_id": "post_456",
            "username": "testuser",
            "text": "What do you think about this topic?",
        }

    @pytest.fixture
    def sample_article(self):
        return "# Test Article\n\n## §1. Introduction\n\n### §1.1 Overview\n\nThis is a test article.\n"

    def test_processor_initialization_with_article_extractor(
        self, mock_instagram_api, mock_llm_client, mock_validator, mock_config, mock_article_extractor
    ):
        """Test that processor accepts and stores a custom article extractor."""
        p = CommentProcessor(
            mock_instagram_api,
            mock_llm_client,
            mock_validator,
            mock_config,
            article_extractor=mock_article_extractor,
        )

        assert p.article_extractor is mock_article_extractor

    def test_articles_from_extractor_converts_correctly(self, processor):
        """Test that _articles_from_extractor converts extractor dicts to processor format."""
        extractor_articles = [
            {
                "id": "art1",
                "title": "Article One",
                "content": "# Article One\n\nFirst paragraph.",
                "link": "https://example.com/1",
            },
            {
                "id": "art2",
                "title": "Article Two",
                "content": "# Article Two\n\nSecond paragraph.",
                "link": "https://example.com/2",
            },
        ]

        articles = processor._articles_from_extractor(extractor_articles)

        assert len(articles) == 2
        assert articles[0]["path"] == "art1"
        assert articles[0]["link"] == "https://example.com/1"
        assert articles[0]["content"] == extractor_articles[0]["content"]
        assert articles[0]["title"] == "Article One"
        assert articles[0]["summary"] == "First paragraph."
        assert articles[0]["is_numbered"] is True
        assert articles[1]["path"] == "art2"
        assert articles[1]["title"] == "Article Two"

    def test_articles_from_extractor_detects_unnumbered_content(self, processor):
        """Test that _articles_from_extractor sets is_numbered=False for content without § markers."""
        extractor_articles = [
            {
                "id": "art1",
                "title": "Plain Article",
                "content": "# Plain Article\n\nNo numbered sections here.",
                "link": "https://example.com/1",
            }
        ]

        articles = processor._articles_from_extractor(extractor_articles)

        assert articles[0]["is_numbered"] is False

    def test_articles_from_extractor_detects_numbered_content(self, processor):
        """Test that _articles_from_extractor sets is_numbered=True when § markers are present."""
        extractor_articles = [
            {
                "id": "art1",
                "title": "Numbered Article",
                "content": "# Numbered Article\n\n## §1. Section\n\nContent.",
                "link": "https://example.com/1",
            }
        ]

        articles = processor._articles_from_extractor(extractor_articles)

        assert articles[0]["is_numbered"] is True

    def test_articles_from_extractor_uses_stored_title_when_no_markdown_heading(self, processor):
        """Test that _articles_from_extractor falls back to stored title when content has no # heading."""
        extractor_articles = [
            {
                "id": "art1",
                "title": "Stored Title",
                "content": "No heading here, just plain text.",
                "link": "https://example.com/1",
            }
        ]

        articles = processor._articles_from_extractor(extractor_articles)

        assert articles[0]["title"] == "Stored Title"

    def test_run_prefers_extractor_articles_over_articles_config(
        self, mock_article_extractor, processor, mock_config, sample_comment, capsys
    ):
        """Test that the article extractor is used instead of ARTICLES_CONFIG when it has articles."""
        mock_article_extractor.get_articles.return_value = [
            {
                "id": "tigris_art1",
                "title": "Tigris Article",
                "content": "# Tigris Article\n\nContent from Tigris.",
                "link": "https://example.com/tigris",
            }
        ]
        # articles_config is also set – extractor should win
        mock_config.articles_config = [{"path": "articles/local.md", "link": "https://example.com/local"}]

        with patch.object(processor, 'load_pending_comments', return_value=[sample_comment]):
            with patch.object(processor, 'process_comment_multi_article', return_value={
                "comment_id": "comment_123",
                "status": "pending_review",
                "article_used": {"path": "tigris_art1", "link": "https://example.com/tigris", "title": "Tigris Article"},
            }) as mock_process:
                with patch.object(processor, 'save_audit_log'):
                    with patch.object(processor, 'post_approved_responses'):
                        with patch.object(processor, 'clear_pending_comments'):
                            processor.run()

        mock_article_extractor.get_articles.assert_called_once()
        mock_process.assert_called_once()
        captured = capsys.readouterr()
        assert "article storage" in captured.out

    def test_run_falls_back_to_articles_config_when_extractor_empty(
        self, mock_article_extractor, processor, mock_config, sample_comment, sample_article, capsys
    ):
        """Test that ARTICLES_CONFIG is used when the article extractor returns no articles."""
        mock_article_extractor.get_articles.return_value = []
        mock_config.articles_config = [{"path": "articles/test.md", "link": "https://example.com/test"}]

        with patch.object(processor, 'load_article', return_value=sample_article) as mock_load:
            with patch.object(processor, 'load_pending_comments', return_value=[sample_comment]):
                with patch.object(processor, 'process_comment', return_value={
                    "comment_id": "comment_123",
                    "status": "pending_review",
                }) as mock_process:
                    with patch.object(processor, 'save_audit_log'):
                        with patch.object(processor, 'post_approved_responses'):
                            with patch.object(processor, 'clear_pending_comments'):
                                processor.run()

        mock_process.assert_called_once()
        mock_load.assert_called_once_with("articles/test.md")

    def test_run_no_articles_anywhere_prints_message(
        self, mock_article_extractor, processor, mock_config, sample_comment, capsys
    ):
        """Test that a clear message is printed when extractor and ARTICLES_CONFIG are both empty."""
        mock_article_extractor.get_articles.return_value = []
        mock_config.articles_config = []

        with patch.object(processor, 'load_pending_comments', return_value=[sample_comment]):
            with patch.object(processor, 'post_approved_responses'):
                with patch.object(processor, 'clear_pending_comments') as mock_clear:
                    processor.run()

        captured = capsys.readouterr()
        assert "No articles configured" in captured.out
        mock_clear.assert_not_called()
