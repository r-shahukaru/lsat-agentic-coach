from __future__ import annotations

import base64
from openai import OpenAI

from services.env import *  # loads .env and checks OPENAI_API_KEY

client = OpenAI()


def read_image_with_openai_vision(image_bytes: bytes) -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    # Responses API expects image_url (can be a data URL)
    data_url = f"data:image/png;base64,{b64}"

    resp = client.responses.create(
        model="gpt-4.1",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Extract all readable text from this image exactly as written. "
                            "Preserve paragraph breaks and line breaks. "
                            "Do not summarize. Do not explain. Output only the extracted text."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": data_url,
                    },
                ],
            }
        ],
        max_output_tokens=4000,
    )

    return (resp.output_text or "").strip()
