"""
scripts/list_blobs.py

Lists recent blobs in the question-images container so you can copy the exact blob_name.

Usage:
  python -m scripts.list_blobs
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
from services.storage_blob import get_blob_storage_from_env


def main() -> None:
    load_dotenv()

    container = os.getenv("BLOB_CONTAINER_IMAGES", "question-images")
    storage = get_blob_storage_from_env()

    print(f"\nListing blobs in container: {container}\n")

    # Listing the latest ~50 blobs (Azure returns in pages; this is enough for our debug).
    container_client = storage._svc.get_container_client(container)
    count = 0
    for blob in container_client.list_blobs():
        print(blob.name)
        count += 1
        if count >= 50:
            break

    if count == 0:
        print("[No blobs found]")

    print("")


if __name__ == "__main__":
    main()
