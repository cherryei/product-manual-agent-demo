from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Optional

from app.config import ALLOWED_UPLOAD_EXTENSIONS, DATA_DIR, UPLOAD_DIR, UPLOADED_MANUALS_FILE
from app.services.language import detect_language
from app.services.products import load_products
from app.services.translation import batch_translate_sections, is_translation_enabled
from app.services.vector_store import get_vector_store, product_chunks


def _uploaded_manuals_path() -> Path:
    UPLOADED_MANUALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    return UPLOADED_MANUALS_FILE


def load_uploaded_manuals() -> list[dict[str, Any]]:
    path = _uploaded_manuals_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_uploaded_manuals(manuals: list[dict[str, Any]]) -> None:
    path = _uploaded_manuals_path()
    path.write_text(json.dumps(manuals, ensure_ascii=False, indent=2), encoding="utf-8")


def is_supported_file(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_UPLOAD_EXTENSIONS


def extract_text_from_pdf(path: Path) -> str:
    from io import StringIO

    from pdfminer.high_level import extract_text_to_fp

    output = StringIO()
    with path.open("rb") as f:
        extract_text_to_fp(f, output)
    text = output.getvalue()
    output.close()
    return text.strip()


def extract_text_from_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _extract_text(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    return extract_text_from_txt(file_path)


def _parse_sections(text: str) -> dict[str, str]:
    """Heuristic section parsing — splits on common heading patterns."""
    import re

    lines = text.splitlines()
    sections: dict[str, str] = {}
    current_section = "content"
    current_lines: list[str] = []

    heading_pattern = re.compile(
        r"^(?:#{1,3}\s+)?(?:\d+[\.\)]\s*)?(?:installation|assembly|safety|warning|care|maintenance|"
        r"specifications|specs|dimensions|faq|overview|introduction|features|parts|"
        r"安装|组装|安全|保养|维护|规格|参数|尺寸|常见问题|概述|简介|特点|部件|功能)",
        re.IGNORECASE,
    )

    for line in lines:
        stripped = line.strip()
        if heading_pattern.match(stripped) and len(stripped) < 100:
            if current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = stripped.lower().replace(" ", "_").replace("#", "").strip()[:30]
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_section] = "\n".join(current_lines).strip()

    return sections or {"content": text}


def process_uploaded_manual(
    file_path: Path,
    original_filename: str,
    title: Optional[str] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_text = _extract_text(file_path)
    if not raw_text:
        raise ValueError(f"No extractable text found in {original_filename}")

    product_id = f"uploaded-{uuid.uuid4().hex[:12]}"
    sections = _parse_sections(raw_text)

    display_title = title or Path(original_filename).stem

    # 检测源语言
    source_language = detect_language(raw_text[:500])  # 用前 500 字符检测语言

    # 构建源语言的结构化数据
    source_sections = {
        "name": display_title,
        "title": f"{display_title} — Uploaded Manual",
        "summary": f"Uploaded product manual from {original_filename} ({len(sections)} sections, {len(raw_text)} chars).",
        "bullets": [f"Source file: {original_filename}", f"Sections: {', '.join(sections.keys())}"],
        "specs": {"Source": original_filename, "Sections": str(len(sections))},
        "installation": sections.get("installation", sections.get("assembly", sections.get("content", ""))),
        "safety": sections.get("safety", "—"),
        "care": sections.get("care", sections.get("maintenance", "—")),
        "faq": "",
    }

    # 自动翻译成 7 种语言
    if is_translation_enabled():
        all_languages = batch_translate_sections(source_sections, source_language)
    else:
        # 翻译不可用时，所有语言都使用源语言内容
        from app.config import SUPPORTED_LANGUAGES
        all_languages = {lang: source_sections.copy() for lang in SUPPORTED_LANGUAGES}

    # 转换为产品数据格式（将字符串转为列表）
    for lang, lang_data in all_languages.items():
        if isinstance(lang_data.get("installation"), str):
            lang_data["installation"] = [line for line in lang_data["installation"].splitlines() if line.strip()]
        if isinstance(lang_data.get("safety"), str):
            lang_data["safety"] = [line for line in lang_data["safety"].splitlines() if line.strip()]
        if isinstance(lang_data.get("care"), str):
            lang_data["care"] = [line for line in lang_data["care"].splitlines() if line.strip()]
        if isinstance(lang_data.get("faq"), str):
            lang_data["faq"] = []
        if isinstance(lang_data.get("bullets"), str):
            lang_data["bullets"] = [lang_data["bullets"]]

    product_entry = {
        "id": product_id,
        "category": "uploaded",
        "image": "",
        "source_notes": f"Uploaded manual: {original_filename}",
        "reference_sources": [original_filename],
        "languages": all_languages,
    }

    manual_record = {
        "product_id": product_id,
        "original_filename": original_filename,
        "file_path": str(file_path),
        "title": display_title,
        "uploaded_at": __import__("datetime").datetime.now().isoformat(),
        "source_language": source_language,
        "char_count": len(raw_text),
        "section_count": len(sections),
        "product_entry": product_entry,
        "translation_enabled": is_translation_enabled(),
    }

    return product_entry, manual_record


def index_uploaded_manual(product_entry: dict[str, Any]) -> int:
    """Add uploaded manual chunks to the vector store."""
    store = get_vector_store()
    chunks = _build_uploaded_chunks(product_entry)
    count = 0
    if hasattr(store, "rows"):
        for chunk in chunks:
            from app.services.embedding import embed_text

            store.rows.append(
                {
                    **chunk,
                    "embedding": embed_text(
                        f"{chunk['product_id']} {chunk['language']} {chunk['section']} {chunk.get('search_text', chunk['text'])}"
                    ),
                }
            )
            count += 1
    elif hasattr(store, "collection") and store.collection.num_entities > 0:
        try:
            from app.services.embedding import embed_text

            store.collection.insert(
                [
                    [chunk["id"] for chunk in chunks],
                    [chunk["product_id"] for chunk in chunks],
                    [chunk["language"] for chunk in chunks],
                    [chunk["section"] for chunk in chunks],
                    [chunk["text"][:4096] for chunk in chunks],
                    [embed_text(chunk.get("search_text", chunk["text"])) for chunk in chunks],
                ]
            )
            store.collection.flush()
            store.collection.load()
            count = len(chunks)
        except Exception:
            count = 0
    return count


def _build_uploaded_chunks(product: dict[str, Any]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    product_id = product["id"]
    for language, data in product["languages"].items():
        search_prefix = f"{product_id} {data['name']} {data['title']}"
        chunks.append(
            {
                "id": f"{product_id}:{language}:overview",
                "product_id": product_id,
                "language": language,
                "section": "overview",
                "text": "\n".join([data["name"], data["title"], data["summary"], *data["bullets"]]),
                "search_text": "\n".join([search_prefix, data["summary"], *data["bullets"]]),
            }
        )
        for section in ["specs", "installation", "safety", "care"]:
            content = data.get(section, "")
            if isinstance(content, list):
                text = "\n".join(content)
            elif isinstance(content, dict):
                text = "\n".join(f"{k}: {v}" for k, v in content.items())
            else:
                text = str(content)
            if text.strip() and text.strip() != "—":
                chunks.append(
                    {
                        "id": f"{product_id}:{language}:{section}",
                        "product_id": product_id,
                        "language": language,
                        "section": section,
                        "text": text,
                        "search_text": "\n".join([search_prefix, section, text]),
                    }
                )
    return chunks


def upload_manual(
    file_path: Path,
    original_filename: str,
    title: Optional[str] = None,
) -> dict[str, Any]:
    product_entry, manual_record = process_uploaded_manual(file_path, original_filename, title)
    manuals = load_uploaded_manuals()
    manuals.append(manual_record)
    save_uploaded_manuals(manuals)
    index_uploaded_manual(product_entry)
    return {**manual_record, "product_entry": product_entry}


def delete_uploaded_manual(product_id: str) -> dict[str, Any]:
    """Remove an uploaded manual: record, source file, vector chunks, and PDFs.

    Raises KeyError if no uploaded manual matches the given product_id.
    """
    from app.config import OUTPUT_DIR

    manuals = load_uploaded_manuals()
    target = next((m for m in manuals if m["product_id"] == product_id), None)
    if target is None:
        raise KeyError(f"No uploaded manual for product_id: {product_id}")

    # 1. Drop the record.
    save_uploaded_manuals([m for m in manuals if m["product_id"] != product_id])

    # 2. Remove the original uploaded file.
    raw_path = target.get("file_path")
    if raw_path:
        Path(raw_path).unlink(missing_ok=True)

    # 3. Remove chunks from the active vector store.
    store = get_vector_store()
    if hasattr(store, "remove_product"):
        try:
            store.remove_product(product_id)
        except Exception:
            pass

    # 4. Remove any generated PDFs for this product.
    removed_pdfs = 0
    for pdf in OUTPUT_DIR.glob(f"{product_id}-manual-*.pdf"):
        pdf.unlink(missing_ok=True)
        removed_pdfs += 1

    return {
        "product_id": product_id,
        "title": target.get("title", ""),
        "removed_pdfs": removed_pdfs,
    }
