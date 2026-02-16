"""
Tigris/S3-compatible storage implementation of audit log storage.
"""
import json
import os
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError

from src.audit_log_extractor import AuditLogExtractor


class TigrisAuditExtractor(AuditLogExtractor):
    """
    Tigris/S3-compatible storage implementation of audit log storage.
    
    Stores audit log entries in an S3-compatible object storage service.
    Default object key: state/audit_log.json
    """

    def __init__(
        self,
        access_key_id: str = None,
        secret_access_key: str = None,
        endpoint_url: str = None,
        bucket_name: str = None,
        region: str = None
    ):
        """
        Initialize Tigris audit log extractor.
        
        Args:
            access_key_id: AWS access key ID (defaults to AWS_ACCESS_KEY_ID env var)
            secret_access_key: AWS secret access key (defaults to AWS_SECRET_ACCESS_KEY env var)
            endpoint_url: S3 endpoint URL (defaults to AWS_ENDPOINT_URL_S3 or
                         https://fly.storage.tigris.dev)
            bucket_name: S3 bucket name (defaults to TIGRIS_BUCKET_NAME env var)
            region: AWS region (defaults to AWS_REGION or 'auto')
        """
        self.access_key_id = access_key_id or os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_access_key = secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY')
        self.endpoint_url = (
            endpoint_url or 
            os.getenv('AWS_ENDPOINT_URL_S3', 'https://fly.storage.tigris.dev')
        )
        self.bucket_name = bucket_name or os.getenv('TIGRIS_BUCKET_NAME')
        self.region = region or os.getenv('AWS_REGION', 'auto')
        self.object_key = "state/audit_log.json"

        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            endpoint_url=self.endpoint_url,
            region_name=self.region
        )

    def save_entry(self, entry: Dict[str, Any]) -> None:
        """
        Save a new audit log entry to S3.
        
        Args:
            entry: Audit log entry data (without ID - will be auto-generated)
        """
        # Load existing entries
        data = self._load_from_s3()
        if data is None:
            data = {"version": "1.0", "entries": []}

        # Auto-generate entry ID
        entry_copy = entry.copy()
        entry_copy["id"] = f"log_{len(data['entries']) + 1:03d}"

        # Append entry
        data["entries"].append(entry_copy)

        # Save to S3
        self._save_to_s3(data)

    def load_entries(self) -> List[Dict[str, Any]]:
        """
        Load all audit log entries from S3.
        
        Returns:
            List of audit log entries, empty list if object doesn't exist
        """
        data = self._load_from_s3()
        if data is None:
            return []
        return data.get("entries", [])

    def update_entry(self, entry_id: str, updates: Dict[str, Any]) -> None:
        """
        Update an existing audit log entry in S3.
        
        Args:
            entry_id: ID of the entry to update
            updates: Dictionary of fields to update
        """
        data = self._load_from_s3()
        if data is None:
            return

        # Find and update entry
        for entry in data.get("entries", []):
            if entry.get("id") == entry_id:
                entry.update(updates)
                break

        # Save updated data
        self._save_to_s3(data)

    def _load_from_s3(self) -> Dict[str, Any]:
        """
        Load data from S3 object.
        
        Returns:
            Parsed JSON data or None if object doesn't exist
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self.object_key
            )
            content = response['Body'].read()
            return json.loads(content.decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise

    def _save_to_s3(self, data: Dict[str, Any]) -> None:
        """
        Save data to S3 object.
        
        Args:
            data: Data to save (will be JSON encoded)
        """
        json_content = json.dumps(data, indent=2)
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=self.object_key,
            Body=json_content,
            ContentType='application/json'
        )
