from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Optional

from app.config import ALIASES_FILE, SUPPORTED_LANGUAGES


@lru_cache
def aliases() -> dict[str, list[str]]:
    return json.loads(ALIASES_FILE.read_text(encoding="utf-8"))


def normalize_language(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    lowered = value.strip().lower()
    for code, names in aliases().items():
        if lowered == code or lowered in [item.lower() for item in names]:
            return code
    return lowered if lowered in SUPPORTED_LANGUAGES else None


def detect_language(text: str, explicit: Optional[str] = None) -> str:
    normalized = normalize_language(explicit)
    if normalized:
        return normalized

    if re.search(r"[\u3040-\u30ff]", text):
        return "jp"
    if re.search(r"[\u3400-\u9fff]", text):
        japanese_markers = ["です", "ます", "ください", "テーブル", "組み立て"]
        return "jp" if any(marker in text for marker in japanese_markers) else "cn"

    lowered = f" {text.lower()} "
    keyword_map = {
        "de": [" wie ", " schraube", " montieren", " tisch", " wasserfest", " pflege"],
        "it": [" come ", " posso ", " tavolo", " montare", " vite", " cura"],
        "fr": [" comment ", " montage", " entretien", " imperméable"],
        "es": [" como ", " cómo ", " mesa", " montar", " tornillo", " cuidado"],
        "cn": [" 怎么 ", " 如何 ", " 安装", " 组装", " 螺丝", " 保养", " 防水", " 尺寸"],
    }
    scores = {
        code: sum(1 for keyword in keywords if keyword in lowered)
        for code, keywords in keyword_map.items()
    }
    best_code, best_score = max(scores.items(), key=lambda item: item[1])
    return best_code if best_score > 0 else "en"


def language_label(code: str) -> str:
    labels = {
        "en": "English",
        "de": "Deutsch",
        "it": "Italiano",
        "fr": "Francais",
        "es": "Espanol",
        "jp": "日本語",
        "cn": "中文",
    }
    return labels.get(code, code)
