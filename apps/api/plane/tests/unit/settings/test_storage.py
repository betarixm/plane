# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os
from unittest.mock import Mock, patch
import pytest
from plane.settings.storage import S3Storage


@pytest.mark.unit
class TestS3StorageSignedURLExpiration:
    """Test the configurable signed URL expiration in S3Storage"""

    @patch.dict(os.environ, {}, clear=True)
    @patch("plane.settings.storage.boto3")
    def test_default_expiration_without_env_variable(self, mock_boto3):
        """Test that default expiration is 3600 seconds when env variable is not set"""
        # Mock the boto3 client
        mock_boto3.client.return_value = Mock()

        # Create S3Storage instance without SIGNED_URL_EXPIRATION env variable
        storage = S3Storage()

        # Assert default expiration is 3600
        assert storage.signed_url_expiration == 3600

    @patch.dict(os.environ, {"SIGNED_URL_EXPIRATION": "30"}, clear=True)
    @patch("plane.settings.storage.boto3")
    def test_custom_expiration_with_env_variable(self, mock_boto3):
        """Test that expiration is read from SIGNED_URL_EXPIRATION env variable"""
        # Mock the boto3 client
        mock_boto3.client.return_value = Mock()

        # Create S3Storage instance with SIGNED_URL_EXPIRATION=30
        storage = S3Storage()

        # Assert expiration is 30
        assert storage.signed_url_expiration == 30

    @patch.dict(os.environ, {"SIGNED_URL_EXPIRATION": "300"}, clear=True)
    @patch("plane.settings.storage.boto3")
    def test_custom_expiration_multiple_values(self, mock_boto3):
        """Test that expiration works with different custom values"""
        # Mock the boto3 client
        mock_boto3.client.return_value = Mock()

        # Create S3Storage instance with SIGNED_URL_EXPIRATION=300
        storage = S3Storage()

        # Assert expiration is 300
        assert storage.signed_url_expiration == 300

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_S3_BUCKET_NAME": "test-bucket",
            "AWS_REGION": "us-east-1",
        },
        clear=True,
    )
    @patch("plane.settings.storage.boto3")
    def test_generate_presigned_post_uses_default_expiration(self, mock_boto3):
        """Test that generate_presigned_post uses the configured default expiration"""
        # Mock the boto3 client and its response
        mock_s3_client = Mock()
        mock_s3_client.generate_presigned_post.return_value = {
            "url": "https://test-url.com",
            "fields": {},
        }
        mock_boto3.client.return_value = mock_s3_client

        # Create S3Storage instance
        storage = S3Storage()

        # Call generate_presigned_post without explicit expiration
        storage.generate_presigned_post("test-object", "image/png", 1024)

        # Assert that the boto3 method was called with the default expiration (3600)
        mock_s3_client.generate_presigned_post.assert_called_once()
        call_kwargs = mock_s3_client.generate_presigned_post.call_args[1]
        assert call_kwargs["ExpiresIn"] == 3600

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_S3_BUCKET_NAME": "test-bucket",
            "AWS_REGION": "us-east-1",
            "SIGNED_URL_EXPIRATION": "60",
        },
        clear=True,
    )
    @patch("plane.settings.storage.boto3")
    def test_generate_presigned_post_uses_custom_expiration(self, mock_boto3):
        """Test that generate_presigned_post uses custom expiration from env variable"""
        # Mock the boto3 client and its response
        mock_s3_client = Mock()
        mock_s3_client.generate_presigned_post.return_value = {
            "url": "https://test-url.com",
            "fields": {},
        }
        mock_boto3.client.return_value = mock_s3_client

        # Create S3Storage instance with SIGNED_URL_EXPIRATION=60
        storage = S3Storage()

        # Call generate_presigned_post without explicit expiration
        storage.generate_presigned_post("test-object", "image/png", 1024)

        # Assert that the boto3 method was called with custom expiration (60)
        mock_s3_client.generate_presigned_post.assert_called_once()
        call_kwargs = mock_s3_client.generate_presigned_post.call_args[1]
        assert call_kwargs["ExpiresIn"] == 60

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_S3_BUCKET_NAME": "test-bucket",
            "AWS_REGION": "us-east-1",
        },
        clear=True,
    )
    @patch("plane.settings.storage.boto3")
    def test_generate_presigned_url_uses_default_expiration(self, mock_boto3):
        """Test that generate_presigned_url uses the configured default expiration"""
        # Mock the boto3 client and its response
        mock_s3_client = Mock()
        mock_s3_client.generate_presigned_url.return_value = "https://test-url.com"
        mock_boto3.client.return_value = mock_s3_client

        # Create S3Storage instance
        storage = S3Storage()

        # Call generate_presigned_url without explicit expiration
        storage.generate_presigned_url("test-object")

        # Assert that the boto3 method was called with the default expiration (3600)
        mock_s3_client.generate_presigned_url.assert_called_once()
        call_kwargs = mock_s3_client.generate_presigned_url.call_args[1]
        assert call_kwargs["ExpiresIn"] == 3600

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_S3_BUCKET_NAME": "test-bucket",
            "AWS_REGION": "us-east-1",
            "SIGNED_URL_EXPIRATION": "30",
        },
        clear=True,
    )
    @patch("plane.settings.storage.boto3")
    def test_generate_presigned_url_uses_custom_expiration(self, mock_boto3):
        """Test that generate_presigned_url uses custom expiration from env variable"""
        # Mock the boto3 client and its response
        mock_s3_client = Mock()
        mock_s3_client.generate_presigned_url.return_value = "https://test-url.com"
        mock_boto3.client.return_value = mock_s3_client

        # Create S3Storage instance with SIGNED_URL_EXPIRATION=30
        storage = S3Storage()

        # Call generate_presigned_url without explicit expiration
        storage.generate_presigned_url("test-object")

        # Assert that the boto3 method was called with custom expiration (30)
        mock_s3_client.generate_presigned_url.assert_called_once()
        call_kwargs = mock_s3_client.generate_presigned_url.call_args[1]
        assert call_kwargs["ExpiresIn"] == 30

    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test-key",
            "AWS_SECRET_ACCESS_KEY": "test-secret",
            "AWS_S3_BUCKET_NAME": "test-bucket",
            "AWS_REGION": "us-east-1",
            "SIGNED_URL_EXPIRATION": "30",
        },
        clear=True,
    )
    @patch("plane.settings.storage.boto3")
    def test_explicit_expiration_overrides_default(self, mock_boto3):
        """Test that explicit expiration parameter overrides the default"""
        # Mock the boto3 client and its response
        mock_s3_client = Mock()
        mock_s3_client.generate_presigned_url.return_value = "https://test-url.com"
        mock_boto3.client.return_value = mock_s3_client

        # Create S3Storage instance with SIGNED_URL_EXPIRATION=30
        storage = S3Storage()

        # Call generate_presigned_url with explicit expiration=120
        storage.generate_presigned_url("test-object", expiration=120)

        # Assert that the boto3 method was called with explicit expiration (120)
        mock_s3_client.generate_presigned_url.assert_called_once()
        call_kwargs = mock_s3_client.generate_presigned_url.call_args[1]
        assert call_kwargs["ExpiresIn"] == 120


@pytest.mark.unit
class TestS3StorageMinioEndpoint:
    @patch.dict(
        os.environ,
        {
            "USE_MINIO": "1",
            "AWS_S3_ENDPOINT_URL": "http://plane-minio:9000",
            "MINIO_ENDPOINT_SSL": "0",
        },
        clear=True,
    )
    @patch("plane.settings.storage.settings.DEBUG", True)
    @patch("plane.settings.storage.boto3")
    def test_debug_request_uses_public_host_with_minio_port(self, mock_boto3):
        request = Mock(scheme="http")
        request.get_host.return_value = "dev.example.com:8000"

        S3Storage(request=request)

        assert mock_boto3.client.call_args.kwargs["endpoint_url"] == "http://dev.example.com:9000"

    @patch.dict(
        os.environ,
        {
            "USE_MINIO": "1",
            "AWS_S3_ENDPOINT_URL": "http://plane-minio:9000",
            "AWS_S3_PUBLIC_ENDPOINT_URL": "https://assets.example.com",
            "MINIO_ENDPOINT_SSL": "0",
        },
        clear=True,
    )
    @patch("plane.settings.storage.settings.DEBUG", True)
    @patch("plane.settings.storage.boto3")
    def test_explicit_public_endpoint_takes_precedence(self, mock_boto3):
        request = Mock(scheme="http")
        request.get_host.return_value = "dev.example.com:8000"

        S3Storage(request=request)

        assert mock_boto3.client.call_args.kwargs["endpoint_url"] == "https://assets.example.com"

    @patch.dict(
        os.environ,
        {
            "USE_MINIO": "1",
            "AWS_S3_ENDPOINT_URL": "http://plane-minio:9000",
            "MINIO_ENDPOINT_SSL": "0",
        },
        clear=True,
    )
    @patch("plane.settings.storage.settings.DEBUG", False)
    @patch("plane.settings.storage.boto3")
    def test_production_request_keeps_proxy_host(self, mock_boto3):
        request = Mock(scheme="https")
        request.get_host.return_value = "plane.example.com"

        S3Storage(request=request)

        assert mock_boto3.client.call_args.kwargs["endpoint_url"] == "https://plane.example.com"
