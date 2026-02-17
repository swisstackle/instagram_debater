"""
Tigris/S3 implementation of posted comments storage.
"""
import os
from typing import Optional, Set

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    ClientError = None
    BOTO3_AVAILABLE = False

from src.posted_comments_extractor import PostedCommentsExtractor


class TigrisPostedExtractor(PostedCommentsExtractor):
    """
    Tigris/S3 implementation of posted comments storage.
    
    Stores posted comment IDs in a text file in S3-compatible object storage.
    Default location: state/posted_ids.txt in the configured bucket.
    """

    def __init__(
        self,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None
    ):
        """
        Initialize Tigris posted comments extractor.
        
        Args:
            access_key_id: AWS access key ID (defaults to AWS_ACCESS_KEY_ID env var)
            secret_access_key: AWS secret access key (defaults to AWS_SECRET_ACCESS_KEY env var)
            endpoint_url: S3 endpoint URL (defaults to AWS_ENDPOINT_URL_S3 or
                         https://fly.storage.tigris.dev)
            bucket_name: S3 bucket name (defaults to TIGRIS_BUCKET_NAME env var)
            region: AWS region (defaults to AWS_REGION or 'auto')
        """
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for Tigris storage. Install it with: pip install boto3")

        # Get configuration from environment variables with fallbacks
        self.access_key_id = access_key_id or os.environ.get("AWS_ACCESS_KEY_ID")
        self.secret_access_key = secret_access_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.endpoint_url = endpoint_url or os.environ.get(
            "AWS_ENDPOINT_URL_S3", "https://fly.storage.tigris.dev"
        )
        self.bucket_name = bucket_name or os.environ.get("TIGRIS_BUCKET_NAME")
        self.region = region or os.environ.get("AWS_REGION", "auto")

        if not self.bucket_name:
            raise ValueError("TIGRIS_BUCKET_NAME environment variable or bucket_name parameter is required")

        # Initialize S3 client
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            endpoint_url=self.endpoint_url,
            region_name=self.region
        )

        self._key = "state/posted_ids.txt"

    def load_posted_ids(self) -> Set[str]:
        """
        Load all posted comment IDs from S3.
        
        Returns:
            Set of comment IDs that have been posted
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=self._key)
            content = response['Body'].read().decode('utf-8')
            lines = content.split('\n')
            # Strip whitespace and filter out empty lines
            return {line.strip() for line in lines if line.strip()}
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                # File doesn't exist yet
                return set()
            raise

    def is_posted(self, comment_id: str) -> bool:
        """
        Check if a comment ID has already been posted.
        
        Args:
            comment_id: The Instagram comment ID to check
            
        Returns:
            True if the comment has been posted, False otherwise
        """
        posted_ids = self.load_posted_ids()
        return comment_id in posted_ids

    def add_posted_id(self, comment_id: str) -> None:
        """
        Add a comment ID to the posted list.
        
        Args:
            comment_id: The Instagram comment ID to mark as posted
        """
        # Load existing IDs
        posted_ids = self.load_posted_ids()

        # Check if already posted to avoid duplicates
        if comment_id in posted_ids:
            return

        # Add new ID
        posted_ids.add(comment_id)

        # Convert to sorted list for consistent ordering
        sorted_ids = sorted(posted_ids)

        # Write back to S3
        content = '\n'.join(sorted_ids) + '\n'
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=self._key,
            Body=content.encode('utf-8')
        )
