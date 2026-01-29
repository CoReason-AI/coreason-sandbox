import base64
import mimetypes
from pathlib import Path
from typing import Protocol

import aiofiles  # type: ignore[import-untyped]
from coreason_identity.models import UserContext

from coreason_sandbox.models import FileReference


class ObjectStorage(Protocol):
    """Protocol for object storage backends (e.g., S3)."""

    async def upload_file(self, file_path: Path, object_name: str, context: UserContext, session_id: str) -> str:
        """Uploads a file to object storage and returns an access URL.

        Args:
            file_path: The local path to the file.
            object_name: The destination object key.
            context: The user context.
            session_id: The session ID.

        Returns:
            str: The URL to access the uploaded file.
        """
        ...


class ArtifactManager:
    """Manages processing of artifacts generated in the sandbox."""

    def __init__(self, storage: ObjectStorage | None = None):
        """Initializes the ArtifactManager.

        Args:
            storage: Optional ObjectStorage backend for uploading non-image artifacts.
        """
        self.storage = storage

    async def process_file(
        self, file_path: Path, original_filename: str, context: UserContext, session_id: str
    ) -> FileReference:
        """Process a local file (downloaded from sandbox) and return a FileReference.

        Converts images to Base64 data URIs.
        Uploads other file types to object storage if configured, returning a signed URL.

        Args:
            file_path: The local path to the artifact file.
            original_filename: The original filename in the sandbox.
            context: The user context.
            session_id: The session ID.

        Returns:
            FileReference: A reference object containing metadata and access URL.

        Raises:
            FileNotFoundError: If the local file path does not exist.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Artifact file not found: {file_path}")  # pragma: no cover

        mime_type, _ = mimetypes.guess_type(original_filename)
        if not mime_type:
            mime_type = "application/octet-stream"  # pragma: no cover

        file_ref = FileReference(
            filename=original_filename,
            path=str(file_path),  # Local path where we stored it temporarily
            content_type=mime_type,
            size_bytes=file_path.stat().st_size,
        )

        # Image processing
        if mime_type.startswith("image/"):
            async with aiofiles.open(file_path, "rb") as f:
                content = await f.read()
                encoded = base64.b64encode(content).decode("utf-8")
                file_ref.url = f"data:{mime_type};base64,{encoded}"

        # Document/Other processing
        elif self.storage:
            try:
                url = await self.storage.upload_file(file_path, original_filename, context, session_id)
                file_ref.url = url
            except Exception:  # pragma: no cover
                # Fallback or log error? For now, leave URL empty if upload fails
                pass

        return file_ref
