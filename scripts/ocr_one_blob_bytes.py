from services.ocr_openai_vision import read_image_with_openai_vision


def run_read_ocr_on_bytes(image_bytes: bytes) -> str:
    return read_image_with_openai_vision(image_bytes)
