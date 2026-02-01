"""
Unit tests for comment processor.
"""
# pylint: disable=too-many-public-methods,line-too-long,too-many-arguments,too-many-positional-arguments
import json
import os
import shutil
import tempfile
from unittest.mock import Mock, patch, mock_open

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
        mock_cfg.article_path = "articles/test.md"
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

    def test_process_comment_success(self, processor, sample_comment, sample_article, mock_instagram_api, mock_llm_client, mock_validator):
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
        mock_validator.validate_response.assert_called_once()
        mock_validator.extract_citations.assert_called_once()

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

    def test_process_comment_validation_fails(self, processor, sample_comment, sample_article, mock_validator):
        """Test processing when validation fails."""
        mock_validator.validate_response.return_value = (False, ["Error 1", "Error 2"])

        result = processor.process_comment(sample_comment, sample_article)

        assert result is not None
        assert result["status"] == "failed"
        assert result["errors"] == ["Error 1", "Error 2"]

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

        audit_data = {
            "version": "1.0",
            "entries": [
                {
                    "comment_id": "comment_123",
                    "generated_response": "Test response",
                    "status": "approved",
                    "posted": False
                }
            ]
        }

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(audit_data))):
                with patch("json.dump") as mock_json_dump:
                    processor.post_approved_responses()

                    # Should post approved responses even when auto-post is disabled
                    mock_instagram_api.post_reply.assert_called_once_with("comment_123", "Test response")

                    # Check that data was updated
                    call_args = mock_json_dump.call_args[0][0]
                    assert call_args["entries"][0]["posted"] is True
                    assert "posted_at" in call_args["entries"][0]

    def test_post_approved_responses_no_audit_file(self, processor, mock_config):
        """Test posting responses when audit file doesn't exist."""
        # AUTO_POST_ENABLED setting should not matter here
        mock_config.auto_post_enabled = True

        with patch("os.path.exists", return_value=False):
            processor.post_approved_responses()

            processor.instagram_api.post_reply.assert_not_called()

    def test_post_approved_responses_success(self, processor, mock_config, mock_instagram_api):
        """Test successfully posting approved responses.

        AUTO_POST_ENABLED should not affect posting of already approved responses.
        """
        # Set to False to emphasize that AUTO_POST_ENABLED doesn't affect approved response posting
        mock_config.auto_post_enabled = False

        audit_data = {
            "version": "1.0",
            "entries": [
                {
                    "comment_id": "comment_123",
                    "generated_response": "Test response",
                    "status": "approved",
                    "posted": False
                },
                {
                    "comment_id": "comment_456",
                    "generated_response": "Another response",
                    "status": "pending_review",
                    "posted": False
                }
            ]
        }

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(audit_data))):
                with patch("json.dump") as mock_json_dump:
                    processor.post_approved_responses()

                    # Should only post the approved one
                    mock_instagram_api.post_reply.assert_called_once_with("comment_123", "Test response")

                    # Check that data was updated
                    call_args = mock_json_dump.call_args[0][0]
                    assert call_args["entries"][0]["posted"] is True
                    assert "posted_at" in call_args["entries"][0]

    def test_post_approved_responses_already_posted(self, processor, mock_config, mock_instagram_api):
        """Test posting responses when already posted."""
        # AUTO_POST_ENABLED should not matter for already posted responses
        mock_config.auto_post_enabled = False

        audit_data = {
            "version": "1.0",
            "entries": [
                {
                    "comment_id": "comment_123",
                    "generated_response": "Test response",
                    "status": "approved",
                    "posted": True
                }
            ]
        }

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(audit_data))):
                with patch("json.dump"):
                    processor.post_approved_responses()

                    # Should not post again
                    mock_instagram_api.post_reply.assert_not_called()

    def test_post_approved_responses_api_exception(self, processor, mock_config, mock_instagram_api):
        """Test posting responses when API raises exception."""
        # AUTO_POST_ENABLED should not affect error handling
        mock_config.auto_post_enabled = False
        mock_instagram_api.post_reply.side_effect = Exception("API Error")

        audit_data = {
            "version": "1.0",
            "entries": [
                {
                    "comment_id": "comment_123",
                    "generated_response": "Test response",
                    "status": "approved",
                    "posted": False
                }
            ]
        }

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(audit_data))):
                with patch("json.dump") as mock_json_dump:
                    processor.post_approved_responses()

                    # Check that error was recorded
                    call_args = mock_json_dump.call_args[0][0]
                    assert "post_error" in call_args["entries"][0]
                    assert call_args["entries"][0]["post_error"] == "API Error"

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
        """Test run method with no pending comments."""
        with patch.object(processor, 'load_article', return_value=sample_article):
            with patch.object(processor, 'load_pending_comments', return_value=[]):
                processor.run()

                captured = capsys.readouterr()
                assert "No pending comments to process" in captured.out

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

    def test_process_comment_multi_article_with_selection(self, processor, sample_comment, mock_llm_client, mock_validator):
        """Test processing comment with multiple articles and article selection."""
        articles = [
            {
                "path": "articles/article1.md",
                "link": "https://example.com/article1",
                "content": "# Article 1\n\n## §1. Section\n\nFitness content.",
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
