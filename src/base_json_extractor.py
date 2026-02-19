"""
Base classes for JSON-based extractors (local disk and Tigris/S3).

Provides common functionality for storage backends that use JSON data structures.
"""
import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    ClientError = None
    BOTO3_AVAILABLE = False

from src.file_utils import load_json_file, save_json_file


class BaseLocalDiskExtractor(ABC):
    """
    Base class for local disk storage extractors.
    
    Provides common functionality for storing JSON data on local filesystem.
    """

    def __init__(self, state_dir: str = "state"):
        """
        Initialize local disk extractor.
        
        Args:
            state_dir: Directory for storing state files (default: "state")
        """
        self.state_dir = state_dir
        os.makedirs(self.state_dir, exist_ok=True)

    @abstractmethod
    def _get_filename(self) -> str:
        """
        Get the filename for this extractor's storage.
        
        Returns:
            Filename (e.g., "pending_comments.json", "audit_log.json")
        """

    def _get_filepath(self) -> str:
        """Get the full file path for storage."""
        return os.path.join(self.state_dir, self._get_filename())

    def _load_data(self, default_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load JSON data from file.
        
        Args:
            default_data: Default data structure if file doesn't exist
            
        Returns:
            Loaded JSON data
        """
        return load_json_file(self._get_filepath(), default_data)

    def _save_data(self, data: Dict[str, Any], ensure_dir: bool = True) -> None:
        """
        Save JSON data to file.
        
        Args:
            data: Data to save
            ensure_dir: Whether to create parent directory if it doesn't exist
        """
        save_json_file(self._get_filepath(), data, ensure_dir=ensure_dir)


class BaseTigrisExtractor(ABC):
    """
    Base class for Tigris/S3-compatible storage extractors.
    
    Provides common functionality for S3-compatible object storage.
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
        Initialize Tigris extractor.
        
        Args:
            access_key_id: AWS access key ID (defaults to AWS_ACCESS_KEY_ID env var)
            secret_access_key: AWS secret access key (defaults to AWS_SECRET_ACCESS_KEY env var)
            endpoint_url: S3 endpoint URL (defaults to AWS_ENDPOINT_URL_S3 or
                         https://fly.storage.tigris.dev)
            bucket_name: S3 bucket name (defaults to TIGRIS_BUCKET_NAME env var)
            region: AWS region (defaults to AWS_REGION or 'auto')
        """
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for Tigris extractors. "
                "Install it with: pip install boto3"
            )

        # Get credentials from parameters or environment variables
        self.access_key_id = access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_access_key = secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.endpoint_url = (
            endpoint_url or 
            os.getenv('AWS_ENDPOINT_URL_S3', 'https://fly.storage.tigris.dev')
        )
        self.bucket_name = bucket_name or os.getenv('TIGRIS_BUCKET_NAME')
        self.region = region or os.getenv('AWS_REGION', 'auto')

        # Validate credentials for TigrisExtractor (optional import check)
        if access_key_id is not None or 'AWS_ACCESS_KEY_ID' in os.environ:
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

    @abstractmethod
    def _get_object_key(self) -> str:
        """
        Get the S3 object key for this extractor's storage.
        
        Returns:
            Object key (e.g., "state/pending_comments.json", "state/audit_log.json")
        """

    def _load_from_s3(self) -> Optional[Dict[str, Any]]:
        """
        Load JSON data from S3 object.
        
        Returns:
            Parsed JSON data or None if object doesn't exist
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self._get_object_key()
            )
            content = response['Body'].read()
            return json.loads(content.decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise

    def _save_to_s3(self, data: Dict[str, Any]) -> None:
        """
        Save JSON data to S3 object.
        
        Args:
            data: Data to save (will be JSON encoded)
        """
        json_content = json.dumps(data, indent=2)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=self._get_object_key(),
            Body=json_content,
            ContentType='application/json',
            CacheControl='no-cache, no-store, must-revalidate'
        )
