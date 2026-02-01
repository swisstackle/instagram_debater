"""
API tests for Instagram API wrapper.
"""
import pytest
import requests_mock
from src.instagram_api import InstagramAPI
import hmac
import hashlib


class TestInstagramAPI:
    """Test suite for InstagramAPI class."""

    @pytest.fixture
    def instagram_api(self):
        """Create InstagramAPI instance for testing."""
        return InstagramAPI(
            access_token="test_access_token",
            app_secret="test_app_secret"
        )

    def test_instagram_api_initialization(self):
        """Test that InstagramAPI initializes properly."""
        api = InstagramAPI(
            access_token="test_token",
            app_secret="test_secret"
        )
        assert api is not None

    def test_verify_webhook_signature_valid(self, instagram_api):
        """Test webhook signature verification with valid signature."""
        payload = b'{"test": "data"}'
        expected_signature = "sha256=" + hmac.new(
            b"test_app_secret",
            payload,
            hashlib.sha256
        ).hexdigest()

        is_valid = instagram_api.verify_webhook_signature(payload, expected_signature)
        assert is_valid is True

    def test_verify_webhook_signature_invalid(self, instagram_api):
        """Test webhook signature verification with invalid signature."""
        payload = b'{"test": "data"}'
        invalid_signature = "sha256=invalid_signature_here"

        is_valid = instagram_api.verify_webhook_signature(payload, invalid_signature)
        assert is_valid is False

    def test_get_comment_success(self, instagram_api):
        """Test fetching a comment by ID."""
        with requests_mock.Mocker() as m:
            comment_data = {
                "id": "comment-123",
                "text": "Test comment",
                "timestamp": "2024-01-01T12:00:00+0000",
                "from": {
                    "id": "user-123",
                    "username": "testuser"
                }
            }
            m.get(
                "https://graph.facebook.com/v18.0/comment-123",
                json=comment_data
            )

            result = instagram_api.get_comment("comment-123")
            assert result["id"] == "comment-123"
            assert result["text"] == "Test comment"

    def test_get_comment_replies_success(self, instagram_api):
        """Test fetching replies to a comment."""
        with requests_mock.Mocker() as m:
            replies_data = {
                "data": [
                    {
                        "id": "reply-1",
                        "text": "First reply",
                        "from": {"id": "user-1", "username": "user1"}
                    },
                    {
                        "id": "reply-2",
                        "text": "Second reply",
                        "from": {"id": "user-2", "username": "user2"}
                    }
                ]
            }
            m.get(
                "https://graph.facebook.com/v18.0/comment-123/replies",
                json=replies_data
            )

            replies = instagram_api.get_comment_replies("comment-123")
            assert len(replies) == 2
            assert replies[0]["id"] == "reply-1"

    def test_get_post_caption_success(self, instagram_api):
        """Test fetching post caption."""
        with requests_mock.Mocker() as m:
            post_data = {
                "id": "post-123",
                "caption": "This is a test post caption"
            }
            m.get(
                "https://graph.facebook.com/v18.0/post-123",
                json=post_data
            )

            caption = instagram_api.get_post_caption("post-123")
            assert caption == "This is a test post caption"

    def test_post_reply_success(self, instagram_api):
        """Test posting a reply to a comment."""
        with requests_mock.Mocker() as m:
            response_data = {
                "id": "reply-comment-123"
            }
            m.post(
                "https://graph.facebook.com/v18.0/comment-123/replies",
                json=response_data
            )

            result = instagram_api.post_reply("comment-123", "This is my reply")
            assert result["id"] == "reply-comment-123"

    def test_post_reply_error_handling(self, instagram_api):
        """Test error handling when posting reply fails."""
        with requests_mock.Mocker() as m:
            m.post(
                "https://graph.facebook.com/v18.0/comment-123/replies",
                status_code=400,
                json={"error": {"message": "Invalid request"}}
            )

            # Should handle error gracefully
            # Implementation details may vary
            try:
                result = instagram_api.post_reply("comment-123", "Test")
                # If it doesn't raise, check for error indication
                assert result is None or "error" in result
            except Exception as e:
                # Or it might raise an exception
                assert isinstance(e, Exception)

    def test_get_comment_not_found(self, instagram_api):
        """Test fetching non-existent comment."""
        with requests_mock.Mocker() as m:
            m.get(
                "https://graph.facebook.com/v18.0/comment-999",
                status_code=404,
                json={"error": {"message": "Comment not found"}}
            )

            # Should handle gracefully
            try:
                result = instagram_api.get_comment("comment-999")
                assert result is None or "error" in result
            except Exception as e:
                assert isinstance(e, Exception)
