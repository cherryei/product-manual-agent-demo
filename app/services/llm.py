from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

from app.config import (
    MODEL_API_KEY,
    MODEL_BASE_URL,
    MODEL_NAME,
    MODEL_PROVIDER,
    MODEL_TIMEOUT_SECONDS,
)
from app.services.vector_store import SearchResult


def is_llm_enabled() -> bool:
    return MODEL_PROVIDER in {"openai", "openai-compatible"} and bool(MODEL_API_KEY and MODEL_NAME)


def generate_with_llm(
    *,
    question: str,
    language: str,
    product_name: str,
    sources: list[SearchResult],
) -> Optional[str]:
    if not is_llm_enabled():
        return None

    context = "\n\n".join(
        f"[{index}] {source.section}: {source.text}"
        for index, source in enumerate(sources, start=1)
    )
    system = (
        "You are a product manual assistant for cross-border furniture buyers. "
        "Answer only from the provided manual context. "
        "If information is missing, say it is not in the manual. "
        f"Use this language code for the answer: {language}."
    )
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Product: {product_name}\n"
                    f"Question: {question}\n\n"
                    f"Manual context:\n{context}"
                ),
            },
        ],
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        f"{MODEL_BASE_URL.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {MODEL_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=MODEL_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
        return None
    return data["choices"][0]["message"]["content"]
