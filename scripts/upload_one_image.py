"""
scripts/upload_one_image.py

Uploads ONE local screenshot to Azure Blob container `question-images`
to verify credentials + storage wiring.

Usage:
  python scripts/upload_one_image.py --file "data/local_images/your.png"

This does NOT do OCR yet. It's only a storage sanity check.
"""

from __future__ import annotations

import os
import argparse
from datetime import datetime
from dotenv import load_dotenv

from services.storage_blob import get_blob_storage_from_env

from datetime import datetime, timezone


def main() -> None:
    # Loading variables from .env into environment.
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to a local image file.")
    parser.add_argument("--user_id", default=os.getenv("DEFAULT_USER_ID", "user01"))
    args = parser.parse_args()

    file_path = args.file
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Reading container name from .env (defaulting to question-images).
    images_container = os.getenv("BLOB_CONTAINER_IMAGES", "question-images")

    # Building a clean blob path (no personal names).
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = os.path.basename(file_path)
    blob_name = f"{args.user_id}/uploads/{ts}-{filename}"

    storage = get_blob_storage_from_env()
    result = storage.upload_file(
        container=images_container,
        file_path=file_path,
        blob_name=blob_name,
    )

    print("\n✅ Upload successful")
    print(f"Container : {result.container}")
    print(f"Blob name : {result.blob_name}")
    print(f"Blob URL  : {result.blob_url}\n")


if __name__ == "__main__":
    main()