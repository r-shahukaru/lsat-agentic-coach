"""
scripts/ocr_one_blob_bytes.py

Downloads an image from Azure Blob Storage (private-safe) and sends BYTES to
Azure AI Vision Read OCR, then prints extracted text.

Usage:
  python -m scripts.ocr_one_blob_bytes --container question-images --blob_name "user01/uploads/....png"
"""

from __future__ import annotations

import os
import time
import argparse
import requests
from dotenv import load_dotenv

from services.storage_blob import get_blob_storage_from_env


def download_blob_bytes(container: str, blob_name: str) -> bytes:
    """Downloading the blob bytes so OCR works even when containers are private."""
    storage = get_blob_storage_from_env()
    blob_client = storage._svc.get_blob_client(container=container, blob=blob_name)  # using existing client
    return blob_client.download_blob().readall()


def run_read_ocr_on_bytes(image_bytes: bytes) -> str:
    """Submitting image bytes to Azure Vision Read API and returning extracted text."""
    endpoint = os.getenv("AZURE_VISION_ENDPOINT", "").strip().rstrip("/")
    key = os.getenv("AZURE_VISION_KEY", "").strip()

    if not endpoint or not key:
        raise RuntimeError("Missing AZURE_VISION_ENDPOINT or AZURE_VISION_KEY in .env")

    read_url = f"{endpoint}/vision/v3.2/read/analyze"
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/octet-stream",
    }

    submit = requests.post(read_url, headers=headers, data=image_bytes)
    if submit.status_code >= 400:
        raise RuntimeError(f"OCR submit failed: {submit.status_code} {submit.text}")

    operation_location = submit.headers.get("Operation-Location")
    if not operation_location:
        raise RuntimeError("Operation-Location header missing from OCR submit response")

    # Polling until we get the result.
    for _ in range(40):
        result = requests.get(operation_location, headers={"Ocp-Apim-Subscription-Key": key})
        if result.status_code >= 400:
            raise RuntimeError(f"OCR poll failed: {result.status_code} {result.text}")

        data = result.json()
        status = data.get("status")

        if status == "succeeded":
            lines = []
            analyze = data.get("analyzeResult", {})
            read_results = analyze.get("readResults", [])
            for page in read_results:
                for line in page.get("lines", []):
                    lines.append(line.get("text", ""))
            return "\n".join(lines).strip()

        if status == "failed":
            raise RuntimeError(f"OCR failed: {data}")

        time.sleep(1)

    raise TimeoutError("OCR polling timed out")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--container", default=os.getenv("BLOB_CONTAINER_IMAGES", "question-images"))
    parser.add_argument("--blob_name", required=True, help='Example: user01/uploads/20260115-232836-test1.png')
    args = parser.parse_args()

    img_bytes = download_blob_bytes(args.container, args.blob_name)
    text = run_read_ocr_on_bytes(img_bytes)

    print("\n===== OCR OUTPUT (BYTES) =====\n")
    print(text if text else "[No text extracted]")
    print("\n==============================\n")


if __name__ == "__main__":
    main()
