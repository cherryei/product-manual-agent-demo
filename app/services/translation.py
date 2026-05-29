"""
文档翻译服务 - 将上传的文档翻译成 7 种语言
"""
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
    SUPPORTED_LANGUAGES,
)


def is_translation_enabled() -> bool:
    """检查翻译功能是否可用（需要 LLM）"""
    return MODEL_PROVIDER in {"openai", "openai-compatible"} and bool(MODEL_API_KEY and MODEL_NAME)


def translate_text(
    text: str,
    source_language: str,
    target_language: str,
    context: str = "product manual",
) -> Optional[str]:
    """
    使用 LLM 翻译文本。

    Args:
        text: 要翻译的文本
        source_language: 源语言代码（如 'en'）
        target_language: 目标语言代码（如 'cn'）
        context: 上下文提示（如 'product manual', 'installation guide'）

    Returns:
        翻译后的文本，失败返回 None
    """
    if not is_translation_enabled():
        return None

    if source_language == target_language:
        return text

    language_names = {
        "en": "English",
        "de": "German",
        "it": "Italian",
        "fr": "French",
        "es": "Spanish",
        "jp": "Japanese",
        "cn": "Chinese",
    }

    source_lang_name = language_names.get(source_language, source_language)
    target_lang_name = language_names.get(target_language, target_language)

    system = (
        f"You are a professional translator specializing in {context}. "
        f"Translate the following text from {source_lang_name} to {target_lang_name}. "
        "Preserve the structure, formatting, and technical terms. "
        "Output ONLY the translated text, no explanations."
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
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
        with urllib.request.urlopen(request, timeout=MODEL_TIMEOUT_SECONDS * 2) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
        return None


def translate_manual_sections(
    sections: dict[str, str],
    source_language: str,
    target_languages: list[str] | None = None,
) -> dict[str, dict[str, str]]:
    """
    将手册的各个章节翻译成多种语言。

    Args:
        sections: 章节字典，如 {"name": "...", "summary": "...", "installation": "..."}
        source_language: 源语言代码
        target_languages: 目标语言列表，默认为所有支持的语言

    Returns:
        多语言字典，如 {"en": {...}, "de": {...}, ...}
    """
    if target_languages is None:
        target_languages = SUPPORTED_LANGUAGES

    result = {}

    # 源语言直接复制
    if source_language in target_languages:
        result[source_language] = sections.copy()

    # 翻译到其他语言
    for target_lang in target_languages:
        if target_lang == source_language:
            continue

        translated_sections = {}
        for key, value in sections.items():
            if not value or not isinstance(value, str):
                translated_sections[key] = value
                continue

            # 翻译每个字段
            translated = translate_text(value, source_language, target_lang, context=f"product manual - {key}")
            translated_sections[key] = translated if translated else value

        result[target_lang] = translated_sections

    return result


def batch_translate_sections(
    sections: dict[str, str],
    source_language: str,
    target_languages: list[str] | None = None,
) -> dict[str, dict[str, str]]:
    """
    批量翻译（优化版）- 将多个字段合并成一次 API 调用。

    Args:
        sections: 章节字典
        source_language: 源语言代码
        target_languages: 目标语言列表

    Returns:
        多语言字典
    """
    if not is_translation_enabled():
        # 翻译不可用时，所有语言都返回源语言内容
        result = {}
        for lang in (target_languages or SUPPORTED_LANGUAGES):
            result[lang] = sections.copy()
        return result

    if target_languages is None:
        target_languages = SUPPORTED_LANGUAGES

    result = {}

    # 源语言直接复制
    if source_language in target_languages:
        result[source_language] = sections.copy()

    # 批量翻译到其他语言
    for target_lang in target_languages:
        if target_lang == source_language:
            continue

        # 将所有字段合并成 JSON 格式
        sections_json = json.dumps(sections, ensure_ascii=False, indent=2)

        language_names = {
            "en": "English",
            "de": "German",
            "it": "Italian",
            "fr": "French",
            "es": "Spanish",
            "jp": "Japanese",
            "cn": "Chinese",
        }

        source_lang_name = language_names.get(source_language, source_language)
        target_lang_name = language_names.get(target_lang, target_lang)

        system = (
            f"You are a professional translator specializing in product manuals. "
            f"Translate the following JSON from {source_lang_name} to {target_lang_name}. "
            "Preserve the JSON structure and keys. Only translate the VALUES. "
            "Output ONLY valid JSON, no explanations."
        )

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": sections_json},
            ],
            "temperature": 0.3,
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
            with urllib.request.urlopen(request, timeout=MODEL_TIMEOUT_SECONDS * 3) as response:
                data = json.loads(response.read().decode("utf-8"))

            translated_json = data["choices"][0]["message"]["content"].strip()
            # 移除可能的 markdown 代码块标记
            if translated_json.startswith("```"):
                lines = translated_json.split("\n")
                translated_json = "\n".join(lines[1:-1]) if len(lines) > 2 else translated_json

            translated_sections = json.loads(translated_json)
            result[target_lang] = translated_sections
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
            # 翻译失败时，回退到源语言内容
            result[target_lang] = sections.copy()

    return result
