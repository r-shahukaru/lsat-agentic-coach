"""
services/storage_blob.py

Uploads files to Azure Blob Storage.

NOTE:
- Images go to container: question-images
- MCQ JSON goes to container: question-metadata
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError


import json
from typing import Any


@dataclass
class BlobUploadResult:
    """Keeping upload result structured for logging and later indexing."""
    container: str
    blob_name: str
    blob_url: str


class AzureBlobStorage:
    """Providing a thin wrapper around Azure Blob APIs."""

    def __init__(self, connection_string: str) -> None:
        # Connecting to Azure Blob Storage using the account connection string.
        self._svc = BlobServiceClient.from_connection_string(connection_string)
        self.service_client = BlobServiceClient.from_connection_string(connection_string)

    def upload_file(self, container: str, file_path: str, blob_name: str) -> BlobUploadResult:
        """
        Uploading a local file to a blob container.

        Args:
            container: Azure Blob container name (e.g., 'question-images').
            file_path: Local path to the file.
            blob_name: Name to store as in Blob (e.g., 'user01/2026-01-15/img1.png').

        Returns:
            BlobUploadResult with the final blob URL.
        """
        # Getting a blob client pointing to the target container/blob path.
        blob_client = self._svc.get_blob_client(container=container, blob=blob_name)

        # Uploading the file bytes (overwriting for quick iteration).
        with open(file_path, "rb") as f:
            blob_client.upload_blob(f, overwrite=True)

        return BlobUploadResult(
            container=container,
            blob_name=blob_name,
            blob_url=blob_client.url,
        )
    
    def list_blobs(self, container: str, prefix: str = "") -> list[str]:
        container_client = self.service_client.get_container_client(container)
        blobs = container_client.list_blobs(name_starts_with=prefix)
        return [b.name for b in blobs]



def get_blob_storage_from_env() -> AzureBlobStorage:
    """Loading Azure Storage connection string from environment variables."""
    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    if not conn:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is missing in your .env")
    return AzureBlobStorage(conn)


def upload_json_to_blob(storage: AzureBlobStorage, container: str, blob_name: str, payload: Any) -> str:
    """Uploading JSON content to blob storage and returning the blob URL."""
    blob_client = storage._svc.get_blob_client(container=container, blob=blob_name)
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    blob_client.upload_blob(data, overwrite=True, content_type="application/json")
    return blob_client.url


def download_json_from_blob(
    storage: AzureBlobStorage,
    container: str,
    blob_name: str,
    *,
    default: Any | None = None,
) -> Any:
    """Downloading a JSON blob and returning the parsed object.

    If the blob does not exist and `default` is provided, returns `default`.
    """
    blob_client = storage._svc.get_blob_client(container=container, blob=blob_name)
    try:
        raw = blob_client.download_blob().readall()
    except ResourceNotFoundError:
        if default is not None:
            return default
        raise

    return json.loads(raw.decode("utf-8"))


def download_blob_bytes(storage: AzureBlobStorage, container: str, blob_name: str) -> bytes:
    """Downloading blob bytes."""
    blob_client = storage._svc.get_blob_client(container=container, blob=blob_name)
    return blob_client.download_blob().readall()


def list_blobs(storage: AzureBlobStorage, container: str, prefix: str = "") -> list[str]:
    return storage.list_blobs(container=container, prefix=prefix)


def list_blob_names(storage: AzureBlobStorage, container: str, prefix: str = "") -> list[str]:
    """Alias for list_blobs(...) for readability in service layers."""
    return list_blobs(storage=storage, container=container, prefix=prefix)

