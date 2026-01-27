# Copyright (c) 2025 CoReason, Inc.
#
# This software is proprietary and dual-licensed.
# Licensed under the Prosperity Public License 3.0 (the "License").
# A copy of the license is available at https://prosperitylicense.com/versions/3.0.0
# For details, see the LICENSE file.
# Commercial use beyond a 30-day trial requires a separate license.
#
# Source Code: https://github.com/CoReason-AI/coreason_sandbox

from pathlib import Path

import anyio
import boto3
from botocore.exceptions import ClientError
from loguru import logger


class S3Storage:
    """S3 implementation of the ObjectStorage protocol."""

    def __init__(
        self,
        bucket: str,
        region: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint_url: str | None = None,
    ):
        """Initializes the S3Storage backend.

        Args:
            bucket: The S3 bucket name.
            region: Optional AWS region name.
            access_key: Optional AWS access key ID.
            secret_key: Optional AWS secret access key.
            endpoint_url: Optional endpoint URL for S3-compatible services (e.g., MinIO).
        """
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
        )

    async def upload_file(self, file_path: Path, object_name: str) -> str:
        """Uploads a file to S3 and returns a presigned URL.

        Args:
            file_path: The local path to the file.
            object_name: The destination object key in S3.

        Returns:
            str: A presigned URL to access the uploaded file.

        Raises:
            FileNotFoundError: If the local file does not exist.
            ClientError: If the upload to S3 fails.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Uploading {file_path} to s3://{self.bucket}/{object_name}")

        def _upload_and_sign() -> str:
            self.client.upload_file(str(file_path), self.bucket, object_name)
            # Generate signed URL (valid for 1 hour)
            url: str = self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": object_name},
                ExpiresIn=3600,
            )
            return url

        try:
            return await anyio.to_thread.run_sync(_upload_and_sign)
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise
