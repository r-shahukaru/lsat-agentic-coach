"""
scripts/ocr_one_blob.py

Runs Azure AI Vision Read OCR on a blob image URL and prints extracted text.

Usage:
  python -m scripts.ocr_one_blob --blob_url "<BLOB_URL_FROM_UPLOAD>"
"""

from __future__ import annotations

import os
import time
import argparse
import requests
from dotenv import load_dotenv


def run_read_ocr(image_url: str) -> str:
    # Loading Azure Vision credentials from environment.
    endpoint = os.getenv("AZURE_VISION_ENDPOINT", "").strip()
    key = os.getenv("AZURE_VISION_KEY", "").strip()

    if not endpoint or not key:
        raise RuntimeError("Missing AZURE_VISION_ENDPOINT or AZURE_VISION_KEY in .env")

    # Normalizing endpoint to avoid double slashes.
    endpoint = endpoint.rstrip("/")

    # Submitting image to Read API (async).
    read_url = f"{endpoint}/vision/v3.2/read/analyze"
    headers = {"Ocp-Apim-Subscription-Key": key}
    payload = {"url": image_url}

    submit = requests.post(read_url, headers=headers, json=payload)
    if submit.status_code >= 400:
        print("OCR submit failed:")
        print("Status:", submit.status_code)
        print("Body:", submit.text)
        submit.raise_for_status()


    operation_location = submit.headers.get("Operation-Location")
    if not operation_location:
        raise RuntimeError("Operation-Location header missing from OCR submit response")

    # Polling the operation endpoint until it succeeds.
    for _ in range(30):  # ~30 seconds max (1 sec sleep)
        result = requests.get(operation_location, headers=headers)
        result.raise_for_status()
        data = result.json()

        status = data.get("status")
        if status == "succeeded":
            # Extracting lines into a readable block of text.
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

    raise TimeoutError("OCR polling timed out (took too long to finish)")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--blob_url", required=True, help="Blob URL of the uploaded image.")
    args = parser.parse_args()

    text = run_read_ocr(args.blob_url)

    print("\n===== OCR OUTPUT =====\n")
    print(text if text else "[No text extracted]")
    print("\n======================\n")


if __name__ == "__main__":
    main()
