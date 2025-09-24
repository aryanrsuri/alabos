"""File handling utilities for alabos - S3 integration and file management."""

import os
import uuid
from typing import Any, BinaryIO
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field


class FileUploadConfig(BaseModel):
    """Configuration for file uploads."""

    bucket_name: str = Field(..., description="S3 bucket name")
    region: str = Field(default="us-east-1", description="AWS region")
    access_key: str | None = Field(default=None, description="AWS access key")
    secret_key: str | None = Field(default=None, description="AWS secret key")
    endpoint_url: str | None = Field(default=None, description="Custom S3 endpoint")
    max_file_size: int = Field(
        default=100 * 1024 * 1024, description="Max file size in bytes (100MB default)"
    )
    allowed_extensions: list[str] = Field(
        default_factory=lambda: [".txt", ".csv", ".json", ".png", ".jpg", ".pdf"]
    )
    public_read: bool = Field(
        default=False, description="Make uploaded files publicly readable"
    )


class FileMetadata(BaseModel):
    """Metadata for uploaded files."""

    file_id: str
    original_filename: str
    content_type: str
    size_bytes: int
    checksum: str
    upload_timestamp: str
    tags: dict[str, str] = Field(default_factory=dict)


class FileHandler:
    """Handles file uploads to S3 and file management."""

    def __init__(self, config: FileUploadConfig):
        self.config = config
        self.s3_client = self._create_s3_client()

    def _create_s3_client(self):
        """Create S3 client with configuration."""
        client_kwargs = {
            "region_name": self.config.region,
        }

        if self.config.access_key and self.config.secret_key:
            client_kwargs["aws_access_key_id"] = self.config.access_key
            client_kwargs["aws_secret_access_key"] = self.config.secret_key

        if self.config.endpoint_url:
            client_kwargs["endpoint_url"] = self.config.endpoint_url

        return boto3.client("s3", **client_kwargs)

    def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
        tags: dict[str, str] | None = None,
    ) -> FileMetadata:
        """Upload a file to S3.

        Args:
            file_data: Binary file data
            filename: Original filename
            content_type: MIME type of the file
            metadata: Additional metadata to store with the file
            tags: Tags to apply to the file

        Returns:
            FileMetadata: Information about the uploaded file

        """
        file_data.seek(0, 2)
        file_size = file_data.tell()
        file_data.seek(0)

        if file_size > self.config.max_file_size:
            raise ValueError(
                f"File size {file_size} exceeds maximum allowed size {self.config.max_file_size}"
            )

        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in self.config.allowed_extensions:
            raise ValueError(
                f"File extension {file_ext} not allowed. Allowed: {self.config.allowed_extensions}"
            )

        file_id = str(uuid.uuid4())
        key = f"alabos/{file_id}/{filename}"

        upload_kwargs = {
            "Bucket": self.config.bucket_name,
            "Key": key,
            "Body": file_data,
            "ContentType": content_type,
            "Metadata": metadata or {},
        }

        if self.config.public_read:
            upload_kwargs["ACL"] = "public-read"

        try:
            response = self.s3_client.put_object(**upload_kwargs)

            if tags:
                self.s3_client.put_object_tagging(
                    Bucket=self.config.bucket_name,
                    Key=key,
                    Tagging={
                        "TagSet": [{"Key": k, "Value": v} for k, v in tags.items()]
                    },
                )

            file_url = self._generate_file_url(key)

            return FileMetadata(
                file_id=file_id,
                original_filename=filename,
                content_type=content_type,
                size_bytes=file_size,
                checksum=response["ETag"].strip('"'),
                upload_timestamp=str(response["LastModified"]),
                tags=tags or {},
            )

        except ClientError as e:
            raise RuntimeError(f"Failed to upload file to S3: {e}")

    def upload_file_from_path(
        self,
        file_path: str,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
        tags: dict[str, str] | None = None,
    ) -> FileMetadata:
        """Upload a file from local path to S3."""
        filename = os.path.basename(file_path)

        if not content_type:
            content_type = self._guess_content_type(filename)

        with open(file_path, "rb") as f:
            return self.upload_file(f, filename, content_type, metadata, tags)

    def download_file(self, file_url: str) -> bytes:
        """Download a file from S3."""
        try:
            parsed_url = urlparse(file_url)
            bucket = parsed_url.netloc.split(".")[0]
            key = parsed_url.path.lstrip("/")

            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()

        except ClientError as e:
            raise RuntimeError(f"Failed to download file from S3: {e}")

    def delete_file(self, file_url: str) -> bool:
        """Delete a file from S3."""
        try:
            parsed_url = urlparse(file_url)
            bucket = parsed_url.netloc.split(".")[0]
            key = parsed_url.path.lstrip("/")

            self.s3_client.delete_object(Bucket=bucket, Key=key)
            return True

        except ClientError as e:
            raise RuntimeError(f"Failed to delete file from S3: {e}")

    def _generate_file_url(self, key: str) -> str:
        """Generate the URL for an uploaded file."""
        if self.config.endpoint_url:
            return f"{self.config.endpoint_url}/{self.config.bucket_name}/{key}"
        else:
            return f"https://{self.config.bucket_name}.s3.{self.config.region}.amazonaws.com/{key}"

    def _guess_content_type(self, filename: str) -> str:
        """Guess MIME type based on file extension."""
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".pdf": "application/pdf",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
        }
        return content_types.get(ext, "application/octet-stream")


_file_handler: FileHandler | None = None


def get_file_handler() -> FileHandler:
    """Get or create the global file handler instance."""
    global _file_handler

    if _file_handler is None:
        config = FileUploadConfig(
            bucket_name=os.getenv("alabos_S3_BUCKET", "alabos-files"),
            region=os.getenv("alabos_S3_REGION", "us-east-1"),
            access_key=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            endpoint_url=os.getenv("alabos_S3_ENDPOINT"),
        )

        _file_handler = FileHandler(config)

    return _file_handler


def upload_task_output_file(
    file_data: BinaryIO,
    filename: str,
    content_type: str,
    task_id: str,
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Upload a file as part of a task output.

    Args:
        file_data: Binary file data
        filename: Original filename
        content_type: MIME type
        task_id: Task ID for organization
        metadata: Additional metadata

    Returns:
        Dict containing file information for task output

    """
    handler = get_file_handler()

    file_metadata = handler.upload_file(
        file_data=file_data,
        filename=filename,
        content_type=content_type,
        metadata=metadata or {},
        tags={"task_id": task_id},
    )

    return {
        "file_url": handler._generate_file_url(
            f"alabos/{file_metadata.file_id}/{filename}"
        ),
        "file_metadata": file_metadata.dict(),
    }
