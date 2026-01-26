from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from coreason_sandbox.storage import S3Storage


@pytest.fixture
def mock_boto3() -> Any:
    with patch("coreason_sandbox.storage.boto3") as mock:
        yield mock


def test_s3_storage_init(mock_boto3: Any) -> None:
    storage = S3Storage(bucket="my-bucket", region="us-east-1")
    mock_boto3.client.assert_called_with(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=None,
        aws_secret_access_key=None,
        endpoint_url=None,
    )
    assert storage.bucket == "my-bucket"


def test_s3_upload_success(mock_boto3: Any, tmp_path: Path) -> None:
    storage = S3Storage(bucket="my-bucket")
    mock_client = mock_boto3.client.return_value
    mock_client.generate_presigned_url.return_value = "https://s3/url"

    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    url = storage.upload_file(test_file, "remote.txt")

    mock_client.upload_file.assert_called_with(str(test_file), "my-bucket", "remote.txt")
    assert url == "https://s3/url"


def test_s3_upload_file_not_found(mock_boto3: Any) -> None:
    storage = S3Storage(bucket="my-bucket")
    with pytest.raises(FileNotFoundError):
        storage.upload_file(Path("nonexistent"), "key")


def test_s3_upload_client_error(mock_boto3: Any, tmp_path: Path) -> None:
    storage = S3Storage(bucket="my-bucket")
    mock_client = mock_boto3.client.return_value
    mock_client.upload_file.side_effect = ClientError({"Error": {"Code": "403", "Message": "Forbidden"}}, "PutObject")

    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    with pytest.raises(ClientError):
        storage.upload_file(test_file, "key")
