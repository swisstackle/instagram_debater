"""
Base test fixtures and helpers for extractor tests.

Provides common test patterns for both comment and audit log extractors.
"""
import json
import os
import shutil
import tempfile
from unittest.mock import Mock, MagicMock

import pytest


class BaseLocalDiskExtractorTests:
    """Base test class for local disk extractors."""

    @pytest.fixture
    def temp_state_dir(self):
        """Create a temporary state directory."""
        temp_dir = tempfile.mkdtemp()
        state_dir = os.path.join(temp_dir, "state")
        os.makedirs(state_dir, exist_ok=True)
        yield state_dir
        shutil.rmtree(temp_dir)


class BaseTigrisExtractorTests:
    """Base test class for Tigris extractors."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock boto3 S3 client."""
        mock_client = MagicMock()
        return mock_client

    def setup_mock_get_object(self, mock_s3_client, data):
        """
        Helper to setup mock get_object response.
        
        Args:
            mock_s3_client: Mock S3 client
            data: Data to return from get_object
        """
        mock_body = Mock()
        mock_body.read.return_value = json.dumps(data).encode('utf-8')
        mock_s3_client.get_object.return_value = {"Body": mock_body}

    def setup_mock_no_such_key(self, mock_s3_client):
        """
        Helper to setup mock NoSuchKey error.
        
        Args:
            mock_s3_client: Mock S3 client
        """
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'NoSuchKey'}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, 'GetObject')
