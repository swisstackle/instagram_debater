"""
Tigris/S3-compatible implementation of comment extractor.
"""
import json
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from src.comment_extractor import CommentExtractor
from src.base_json_extractor import BaseTigrisExtractor


class TigrisExtractor(BaseTigrisExtractor, CommentExtractor):
    """Comment extractor that uses Tigris/S3-compatible object storage."""

    def _get_object_key(self) -> str:
        """Get the S3 object key for comment storage."""
        return "state/pending_comments.json"

    def load_pending_comments(self) -> List[Dict[str, Any]]:
        """
        Load pending comments from Tigris object storage.

        Returns:
            List of pending comment dictionaries
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self._get_object_key()
            )
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            return data.get("comments", [])
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                # Object doesn't exist yet, return empty list
                return []
            raise

    def save_pending_comment(self, comment_data: Dict[str, Any]) -> None:
        """
        Save a single pending comment to Tigris object storage.

        Args:
            comment_data: Comment data to save
        """
        # Load existing comments
        comments = self.load_pending_comments()
        
        # Append new comment
        comments.append(comment_data)
        
        # Save back to storage
        data = {"version": "1.0", "comments": comments}
        self._save_to_s3(data)

    def clear_pending_comments(self) -> None:
        """Clear all pending comments from Tigris storage."""
        data = {"version": "1.0", "comments": []}
        self._save_to_s3(data)
