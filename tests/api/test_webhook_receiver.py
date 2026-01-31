"""
API tests for webhook receiver.
"""
import pytest
import json
import hmac
import hashlib
from unittest.mock import patch, mock_open, MagicMock
from src.webhook_receiver import WebhookReceiver


class TestWebhookReceiver:
    """Test suite for WebhookReceiver class."""
    
    @pytest.fixture
    def webhook_receiver(self):
        """Create WebhookReceiver instance for testing."""
        return WebhookReceiver(
            verify_token="test_verify_token",
            app_secret="test_app_secret"
        )
    
    def test_webhook_receiver_initialization(self):
        """Test that WebhookReceiver initializes properly."""
        receiver = WebhookReceiver(
            verify_token="test_token",
            app_secret="test_secret"
        )
        assert receiver is not None
    
    def test_verify_challenge_valid(self, webhook_receiver):
        """Test webhook verification with valid token."""
        result = webhook_receiver.verify_challenge(
            mode="subscribe",
            token="test_verify_token",
            challenge="test_challenge_123"
        )
        assert result == "test_challenge_123"
    
    def test_verify_challenge_invalid_token(self, webhook_receiver):
        """Test webhook verification with invalid token."""
        result = webhook_receiver.verify_challenge(
            mode="subscribe",
            token="wrong_token",
            challenge="test_challenge_123"
        )
        assert result is None
    
    def test_verify_challenge_invalid_mode(self, webhook_receiver):
        """Test webhook verification with invalid mode."""
        result = webhook_receiver.verify_challenge(
            mode="invalid_mode",
            token="test_verify_token",
            challenge="test_challenge_123"
        )
        assert result is None
    
    def test_extract_comment_data_valid_payload(self, webhook_receiver):
        """Test extracting comment data from valid webhook entry."""
        entry = {
            "id": "account-123",
            "time": 1704067200,
            "changes": [
                {
                    "field": "comments",
                    "value": {
                        "from": {
                            "id": "user-123",
                            "username": "testuser"
                        },
                        "media": {
                            "id": "media-456",
                            "media_product_type": "FEED"
                        },
                        "id": "comment-789",
                        "text": "Test comment text"
                    }
                }
            ]
        }
        
        comment_data = webhook_receiver.extract_comment_data(entry)
        assert comment_data is not None
        assert comment_data["comment_id"] == "comment-789"
        assert comment_data["text"] == "Test comment text"
    
    def test_extract_comment_data_no_comments(self, webhook_receiver):
        """Test extracting comment data from entry with no comments."""
        entry = {
            "id": "account-123",
            "time": 1704067200,
            "changes": [
                {
                    "field": "other_field",
                    "value": {}
                }
            ]
        }
        
        comment_data = webhook_receiver.extract_comment_data(entry)
        assert comment_data is None
    
    def test_process_webhook_payload_with_comments(self, webhook_receiver):
        """Test processing webhook payload containing comments."""
        payload = {
            "object": "instagram",
            "entry": [
                {
                    "id": "account-123",
                    "time": 1704067200,
                    "changes": [
                        {
                            "field": "comments",
                            "value": {
                                "from": {
                                    "id": "user-123",
                                    "username": "testuser"
                                },
                                "media": {
                                    "id": "media-456"
                                },
                                "id": "comment-789",
                                "text": "Test comment"
                            }
                        }
                    ]
                }
            ]
        }
        
        # Mock the save_pending_comment method to verify it's called
        with patch.object(webhook_receiver, 'save_pending_comment') as mock_save:
            webhook_receiver.process_webhook_payload(payload)
            
            # Verify save_pending_comment was called once
            assert mock_save.call_count == 1
            
            # Verify the comment data passed to save_pending_comment
            call_args = mock_save.call_args[0][0]
            assert call_args["comment_id"] == "comment-789"
            assert call_args["username"] == "testuser"
            assert call_args["text"] == "Test comment"
    
    def test_save_pending_comment(self, webhook_receiver):
        """Test saving comment to pending_comments.json."""
        comment_data = {
            "comment_id": "123",
            "post_id": "456",
            "username": "testuser",
            "user_id": "789",
            "text": "Test comment",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        # Mock file operations to verify json.dump is called correctly
        mock_file_data = json.dumps({"version": "1.0", "comments": []})
        
        with patch("builtins.open", mock_open(read_data=mock_file_data)) as mock_file:
            with patch("json.dump") as mock_json_dump:
                with patch("os.path.exists", return_value=True):
                    with patch("os.makedirs"):
                        webhook_receiver.save_pending_comment(comment_data)
                        
                        # Verify json.dump was called
                        assert mock_json_dump.call_count == 1
                        
                        # Verify the data passed to json.dump
                        saved_data = mock_json_dump.call_args[0][0]
                        assert saved_data["version"] == "1.0"
                        assert len(saved_data["comments"]) == 1
                        assert saved_data["comments"][0]["comment_id"] == "123"
                        assert saved_data["comments"][0]["username"] == "testuser"
                        assert saved_data["comments"][0]["text"] == "Test comment"
    #         "entry": [
    #             {
    #                 "id": "account-123",
    #                 "time": 1704067200,
    #                 "changes": [
    #                     {
    #                         "field": "comments",
    #                         "value": {
    #                             "from": {"id": "user-123", "username": "testuser"},
    #                             "media": {"id": "media-456"},
    #                             "id": "comment-789",
    #                             "text": "Test"
    #                         }
    #                     }
    #                 }
    #             }
    #         ]
    #     }
    #     
    #     # Create INVALID signature
    #     invalid_signature = "sha256=invalid_signature_here"
    #     
    #     response = client.post(
    #         "/webhook/instagram",
    #         json=payload,
    #         headers={"X-Hub-Signature-256": invalid_signature}
    #     )
    #     
    #     # Should reject with 403 Forbidden
    #     assert response.status_code == 403
