from __future__ import annotations

from typing import List

def retrieve_context(query: str, k: int = 5) -> List[str]:
    """
    Returns the top k similar text chunks from the embedded RAG corpus,
    concatenated or in a list for context injection.
    """
    res = self.search(query, top_k=k)
    return [r["text"] for r in res]
