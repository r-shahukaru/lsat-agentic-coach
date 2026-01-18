from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict, Optional, List


class MCQItem(BaseModel):
    """Storing one LSAT-style multiple-choice question."""
    id: str
    source_blob_name: str
    question: str
    options: Dict[str, str] = Field(description="Option map like {'A': '...', 'B': '...'}")
    subtype: str = "Unknown"
    ocr_text: str

    # Optional enrichment fields (we'll use later).
    paraphrased_question: Optional[str] = None
    paraphrased_options: Optional[Dict[str, str]] = None
