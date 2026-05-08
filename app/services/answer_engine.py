from __future__ import annotations

from typing import Optional

from app.services.language import detect_language, language_label
from app.services.llm import generate_with_llm, is_llm_enabled
from app.services.products import get_product, match_product_id
from app.services.vector_store import SearchResult, get_vector_store


SECTION_TITLES = {
    "en": {
        "intro": "Answer",
        "sources": "Relevant manual sections",
        "not_found": "I could not find an exact section. Here is the closest manual content.",
    },
    "de": {
        "intro": "Antwort",
        "sources": "Relevante Abschnitte der Anleitung",
        "not_found": "Ich konnte keinen exakten Abschnitt finden. Hier ist der naechste passende Inhalt.",
    },
    "it": {
        "intro": "Risposta",
        "sources": "Sezioni rilevanti del manuale",
        "not_found": "Non ho trovato una sezione esatta. Ecco il contenuto piu vicino.",
    },
    "fr": {
        "intro": "Reponse",
        "sources": "Sections pertinentes du manuel",
        "not_found": "Je n'ai pas trouve de section exacte. Voici le contenu le plus proche.",
    },
    "es": {
        "intro": "Respuesta",
        "sources": "Secciones relevantes del manual",
        "not_found": "No encontre una seccion exacta. Este es el contenido mas cercano.",
    },
    "jp": {
        "intro": "回答",
        "sources": "関連する説明書セクション",
        "not_found": "完全に一致する項目は見つかりませんでした。最も近い内容を表示します。",
    },
    "cn": {
        "intro": "回答",
        "sources": "相关说明书章节",
        "not_found": "未找到完全匹配的章节，以下是最接近的说明书内容。",
    },
}

SECTION_LABELS = {
    "overview": {"en": "Overview", "de": "Uebersicht", "it": "Panoramica", "fr": "Apercu", "es": "Resumen", "jp": "概要", "cn": "概览"},
    "specs": {"en": "Specifications", "de": "Daten", "it": "Specifiche", "fr": "Caracteristiques", "es": "Especificaciones", "jp": "仕様", "cn": "规格"},
    "installation": {"en": "Installation", "de": "Montage", "it": "Installazione", "fr": "Montage", "es": "Instalacion", "jp": "組み立て", "cn": "安装"},
    "safety": {"en": "Safety", "de": "Sicherheit", "it": "Sicurezza", "fr": "Securite", "es": "Seguridad", "jp": "安全", "cn": "安全"},
    "care": {"en": "Care", "de": "Pflege", "it": "Cura", "fr": "Entretien", "es": "Cuidado", "jp": "お手入れ", "cn": "保养"},
    "faq": {"en": "FAQ", "de": "FAQ", "it": "FAQ", "fr": "FAQ", "es": "FAQ", "jp": "FAQ", "cn": "常见问题"},
}


def _section_label(section: str, language: str) -> str:
    return SECTION_LABELS.get(section, {}).get(language, section.title())


def _first_relevant_sentence(results: list[SearchResult]) -> str:
    if not results:
        return ""
    lines = [line.strip() for line in results[0].text.splitlines() if line.strip()]
    return lines[0] if lines else results[0].text


def _best_product_id(results: list[SearchResult], fallback_product_id: str) -> str:
    return results[0].product_id if results else fallback_product_id


def answer_question(
    question: str,
    *,
    product_id: Optional[str] = None,
    language: Optional[str] = None,
) -> tuple[str, str, str, list[SearchResult]]:
    detected_language = detect_language(question, language)
    store = get_vector_store()
    if product_id:
        product = get_product(product_id)
        results = store.search(
            question,
            product_id=product["id"],
            language=detected_language,
            limit=4,
        )
        selected_product_id = product["id"]
    else:
        matched_product_id = match_product_id(question, detected_language)
        if matched_product_id:
            product = get_product(matched_product_id)
            results = store.search(
                question,
                product_id=matched_product_id,
                language=detected_language,
                limit=4,
            )
            selected_product_id = matched_product_id
        else:
            broad_results = store.search(
                question,
                product_id=None,
                language=detected_language,
                limit=8,
            )
            selected_product_id = _best_product_id(broad_results, get_product()["id"])
            product = get_product(selected_product_id)
            results = [
                result for result in broad_results if result.product_id == selected_product_id
            ][:4] or store.search(
                question,
                product_id=selected_product_id,
                language=detected_language,
                limit=4,
            )

    localized = product["languages"].get(detected_language) or product["languages"]["en"]

    copy = SECTION_TITLES[detected_language]
    lead = _first_relevant_sentence(results)
    if not lead:
        lead = localized["summary"]

    llm_answer = generate_with_llm(
        question=question,
        language=detected_language,
        product_name=localized["name"],
        sources=results,
    )
    if llm_answer:
        answer_lines = [
            f"{copy['intro']} ({language_label(detected_language)}, LLM)",
            "",
            llm_answer,
            "",
            copy["sources"],
        ]
        for index, result in enumerate(results, start=1):
            label = _section_label(result.section, detected_language)
            clipped = " ".join(result.text.split())[:520]
            answer_lines.append(f"{index}. {label}: {clipped}")
        return "\n".join(answer_lines), detected_language, selected_product_id, results

    mode_label = "Local retrieval" if not is_llm_enabled() else "Local fallback"
    answer_lines = [
        f"{copy['intro']} ({language_label(detected_language)}, {mode_label})",
        "",
        f"{localized['name']}: {lead}",
        "",
        copy["sources"],
    ]
    for index, result in enumerate(results, start=1):
        label = _section_label(result.section, detected_language)
        clipped = " ".join(result.text.split())[:520]
        answer_lines.append(f"{index}. {label}: {clipped}")
    return "\n".join(answer_lines), detected_language, selected_product_id, results
