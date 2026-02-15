"""
Tigris/S3-compatible implementation of comment extractor.
"""
import json
import os
from typing import Any, Dict, List, Optional

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = None

from src.comment_extractor import CommentExtractor


class TigrisExtractor(CommentExtractor):
    """Comment extractor that uses Tigris/S3-compatible object storage."""

    def __init__(
        self,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None
    ):
        """
        Initialize Tigris extractor.

        Args:
            access_key_id: AWS access key ID (defaults to AWS_ACCESS_KEY_ID env var)
            secret_access_key: AWS secret access key (defaults to AWS_SECRET_ACCESS_KEY env var)
            endpoint_url: S3 endpoint URL (defaults to AWS_ENDPOINT_URL_S3 env var)
            bucket_name: Tigris bucket name (defaults to TIGRIS_BUCKET_NAME env var)
            region: AWS region (defaults to AWS_REGION env var or 'auto')
        """
        if boto3 is None:
            raise ImportError(
                "boto3 is required for TigrisExtractor. "
                "Install it with: pip install boto3"
            )

        # Get credentials from parameters or environment variables
        self.access_key_id = access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_access_key = secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.endpoint_url = endpoint_url or os.getenv(
            'AWS_ENDPOINT_URL_S3',
            'https://fly.storage.tigris.dev'
        )
        self.bucket_name = bucket_name or os.getenv('TIGRIS_BUCKET_NAME')
        self.region = region or os.getenv('AWS_REGION', 'auto')

        if not self.access_key_id or not self.secret_access_key:
            raise ValueError(
                "AWS credentials are required. Set AWS_ACCESS_KEY_ID and "
                "AWS_SECRET_ACCESS_KEY environment variables or pass them as parameters."
            )

        if not self.bucket_name:
            raise ValueError(
                "Bucket name is required. Set TIGRIS_BUCKET_NAME environment variable "
                "or pass it as a parameter."
            )

        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            endpoint_url=self.endpoint_url,
            region_name=self.region
        )

        self.object_key = "state/pending_comments.json"

    def load_pending_comments(self) -> List[Dict[str, Any]]:
        """
        Load pending comments from Tigris object storage.

        Returns:
            List of pending comment dictionaries
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self.object_key
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
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=self.object_key,
            Body=json.dumps(data, indent=2),
            ContentType='application/json'
        )

    def clear_pending_comments(self) -> None:
        """Clear all pending comments from Tigris storage."""
        data = {"version": "1.0", "comments": []}
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=self.object_key,
            Body=json.dumps(data, indent=2),
            ContentType='application/json'
        )
